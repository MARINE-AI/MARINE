import asyncio
import os
import shlex
import json
import platform
import glob
from urllib.parse import urlparse, parse_qs
import httpx  # Async HTTP client
from aiokafka import AIOKafkaConsumer
from app.kafka_client import get_kafka_producer, get_kafka_consumer
from app.config import settings
from loguru import logger

# Define a minimum video size in bytes. Adjust as needed.
MIN_VIDEO_SIZE = 1024

def shell_quote(arg: str) -> str:
    """
    Quote an argument for the shell.
    On Windows, wrap in double quotes; on POSIX, use shlex.quote.
    """
    if platform.system() == "Windows":
        return '"{}"'.format(arg.replace('"', ''))
    return shlex.quote(arg)

async def run_command(cmd: str, stdin=None):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdin=stdin,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return process

async def process_video_task(message_value: bytes):
    """
    Downloads a video using yt-dlp, segments it with ffmpeg, and then automatically sends
    each chunk to the AI microservice's endpoints:
      - /upload-video-chunk for each chunk
      - /match-video-chunks to trigger matching after all chunks are sent.
    """
    try:
        msg = json.loads(message_value.decode("utf-8"))
        video_url = msg.get("video_url")
        if not video_url:
            logger.error("No video_url found in the message")
            return

        # Normalize YouTube embed URLs to standard watch URLs.
        if "youtube.com/embed/" in video_url:
            video_url = video_url.replace("youtube.com/embed/", "youtube.com/watch?v=")

        # Derive a filename-friendly video ID.
        parsed_url = urlparse(video_url)
        if "youtube.com" in parsed_url.netloc or "youtu.be" in parsed_url.netloc:
            query = parse_qs(parsed_url.query)
            if "v" in query and query["v"]:
                video_id = query["v"][0]
            else:
                video_id = os.path.basename(parsed_url.path)
        else:
            video_id = os.path.basename(video_url).split("?")[0] or "video"

        logger.info(f"Processing video: {video_url}")

        # Ensure downloads directory exists.
        downloads_dir = os.path.join(os.getcwd(), "downloads")
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
            logger.info(f"Created downloads directory: {downloads_dir}")

        # Download the video using yt-dlp with a template preserving the native extension.
        video_template = os.path.join(downloads_dir, f"{video_id}.%(ext)s")
        yt_dlp_cmd = f"yt-dlp -f best -o {shell_quote(video_template)} {shell_quote(video_url)}"
        logger.info(f"Running yt-dlp command: {yt_dlp_cmd}")
        proc = await run_command(yt_dlp_cmd)
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(f"yt-dlp failed: {stderr.decode('utf-8')}")
            return

        # Wait briefly for the file system to update.
        await asyncio.sleep(2)
        matching_files = glob.glob(os.path.join(downloads_dir, f"{video_id}.*"))
        if not matching_files:
            logger.error(f"Downloaded video file is missing for video_id '{video_id}'")
            return

        video_file = matching_files[0]
        file_size = os.path.getsize(video_file)
        logger.info(f"Downloaded video file: {video_file}, size: {file_size} bytes")
        if file_size < MIN_VIDEO_SIZE:
            logger.warning("Downloaded video file is too small; sending as a raw chunk.")
            async with httpx.AsyncClient() as client:
                with open(video_file, "rb") as f:
                    chunk_data = f.read()
                data = {"video_id": video_id, "chunk_index": 0, "total_chunks": 1}
                files = {"video_chunk": (f"{video_id}.mp4", chunk_data, "video/mp4")}
                resp = await client.post(f"{settings.AI_MICROSERVICE_URL}/upload-video-chunk", data=data, files=files)
                logger.info(f"Sent raw chunk for video {video_id} (status: {resp.status_code})")
            return

        # Segment the video using ffmpeg.
        output_pattern = os.path.join(downloads_dir, f"{video_id}_chunk_%03d.mp4")
        ffmpeg_cmd = (
            f"ffmpeg -hide_banner -loglevel error -i {shell_quote(video_file)} "
            f"-c copy -map 0 -f segment -segment_time {settings.segment_duration} "
            f"-reset_timestamps 1 {shell_quote(output_pattern)}"
        )
        logger.info(f"Running ffmpeg command: {ffmpeg_cmd}")
        proc_ffmpeg = await run_command(ffmpeg_cmd)
        stdout_ff, stderr_ff = await proc_ffmpeg.communicate()
        if proc_ffmpeg.returncode != 0:
            logger.error(f"ffmpeg failed: {stderr_ff.decode('utf-8')}")
            return

        chunk_files = sorted([
            os.path.join(downloads_dir, f) for f in os.listdir(downloads_dir)
            if f.startswith(f"{video_id}_chunk_") and f.endswith(".mp4")
        ])
        if not chunk_files:
            logger.error("No video chunks produced, skipping further processing.")
            return

        total_chunks = len(chunk_files)
        logger.info(f"Found {total_chunks} chunks for video {video_id}")

        # Send each chunk to the AI microservice.
        async with httpx.AsyncClient() as client:
            for idx, chunk_file in enumerate(chunk_files):
                with open(chunk_file, "rb") as f:
                    chunk_data = f.read()
                data = {
                    "video_id": video_id,
                    "chunk_index": idx,
                    "total_chunks": total_chunks
                }
                files = {"video_chunk": (f"chunk_{idx}.mp4", chunk_data, "video/mp4")}
                resp = await client.post(f"{settings.AI_MICROSERVICE_URL}/upload-video-chunk", data=data, files=files)
                logger.info(f"Sent chunk {idx} for video {video_id} (status: {resp.status_code})")

            # After all chunks are sent, trigger matching.
            match_data = {"video_id": video_id, "total_chunks": total_chunks}
            resp = await client.post(f"{settings.AI_MICROSERVICE_URL}/match-video-chunks", data=match_data)
            logger.info(f"Triggered match processing for video {video_id} (status: {resp.status_code})")
            logger.info(f"Match response: {resp.text}")

    except Exception as e:
        logger.error(f"Error processing video task: {e}")

async def video_downloader_worker():
    """
    Consumes Kafka messages from the video download topic and processes each video task.
    """
    consumer = await get_kafka_consumer(settings.kafka_video_download_topic, group_id="video_downloader_group")
    try:
        async for msg in consumer:
            logger.info(f"Received video download task: {msg.value}")
            await process_video_task(msg.value)
    except Exception as e:
        logger.error(f"Error in video_downloader_worker: {e}")
    finally:
        await consumer.stop()

def run_video_downloader():
    """
    Runs the video downloader worker.
    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(video_downloader_worker())
