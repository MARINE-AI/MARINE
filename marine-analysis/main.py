import os
import subprocess
import glob
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from fingerprint.video import extract_keyframes, compute_phashes, compute_video_similarity
from fingerprint.audio import extract_audio, generate_audio_fingerprint

from storage.redis_utils import get_phashes, store_phashes
from config import settings
from db import async_session, UploadedVideo, CrawledVideo, init_db
from sqlalchemy import select, text
from loguru import logger
from broadcaster import broadcaster

def cleanup_files(file_list: list):
    for file_path in file_list:
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to remove file {file_path}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    await init_db()
    if not os.path.exists(settings.FRAMES_DIR):
        os.makedirs(settings.FRAMES_DIR)
        logger.info(f"Created frames directory: {settings.FRAMES_DIR}")
    yield
    logger.info("Shutting down application...")
    logger.info("Shutdown complete.")

app = FastAPI(lifespan=lifespan, title="Video AI Microservice")

@app.get("/sse")
async def sse(request: Request, user_email: str = Form(...)):
    async def event_generator(queue: asyncio.Queue):
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            await broadcaster.unsubscribe(user_email, queue)
    queue = await broadcaster.subscribe(user_email)
    return StreamingResponse(event_generator(queue), media_type="text/event-stream")

@app.post("/match-video")
async def match_video(
    video_file: UploadFile = File(...),
    user_email: str = Form(...)
):
    filename = video_file.filename
    video_id = f"full_{filename}"
    temp_path = f"temp_{filename}"
    with open(temp_path, "wb") as f:
        f.write(await video_file.read())
    pattern = os.path.join(settings.FRAMES_DIR, f"uploaded_{filename}_%d.jpg")
    try:
        frames = extract_keyframes(temp_path, pattern, fps=1)
        if not frames:
            return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from uploaded video."})
        phashes = compute_phashes(frames)
        audio_file = "temp_audio.wav"
        extracted_audio = extract_audio(temp_path, audio_file)
        audio_fp = generate_audio_fingerprint(extracted_audio) if extracted_audio else None

        match_results = await match_against_crawled(phashes, video_id)
        flagged = True if match_results else False

        async with async_session() as session:
            existing = await session.get(UploadedVideo, video_id)
            if existing:
                existing.match_score = 0.0
                existing.uploaded_phashes = phashes
                existing.audio_spectrum = audio_fp
                existing.flagged = flagged
                existing.user_email = user_email
                session.add(existing)
            else:
                new_record = UploadedVideo(
                    video_id=video_id,
                    video_url="uploaded",
                    match_score=0.0,
                    uploaded_phashes=phashes,
                    audio_spectrum=audio_fp,
                    flagged=flagged,
                    user_email=user_email
                )
                session.add(new_record)
            await session.commit()

        status_message = f"Video '{filename}' processed. Flagged: {flagged}. Matches: {match_results}"
        await broadcaster.broadcast(user_email, status_message)

        response = {
            "video_id": video_id,
            "flagged": flagged,
            "active_matches": match_results
        }
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in /match-video: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during video analysis.")
    finally:
        cleanup_files([temp_path])
        cleanup_files(frames)

CHUNKS_DIR = os.path.join(os.getcwd(), "video_chunks")
if not os.path.exists(CHUNKS_DIR):
    os.makedirs(CHUNKS_DIR)

@app.post("/upload-video-chunk")
async def upload_video_chunk(
    background_tasks: BackgroundTasks,
    video_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    video_chunk: UploadFile = File(...)
):
    chunk_dir = os.path.join(CHUNKS_DIR, video_id)
    if not os.path.exists(chunk_dir):
        os.makedirs(chunk_dir)
    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}.mp4")
    with open(chunk_path, "wb") as f:
        f.write(await video_chunk.read())
    existing_chunks = glob.glob(os.path.join(chunk_dir, "chunk_*.mp4"))
    if len(existing_chunks) == total_chunks:
        background_tasks.add_task(process_chunks_and_match, video_id, total_chunks)
    return JSONResponse({"message": f"Chunk {chunk_index} for video {video_id} uploaded successfully."})

@app.post("/analyze")
async def analyze(video_id: str = Form(...), total_chunks: int = Form(...)):
    result = await process_chunks_and_match(video_id, total_chunks)
    if not result:
        raise HTTPException(status_code=400, detail="Processing failed.")
    return JSONResponse(content=result)

def reassemble_video(video_id: str, total_chunks: int) -> str:
    chunk_dir = os.path.join(CHUNKS_DIR, video_id)
    if not os.path.exists(chunk_dir):
        raise Exception("No chunks found for this video_id.")
    chunk_files = sorted(
        glob.glob(os.path.join(chunk_dir, "chunk_*.mp4")),
        key=lambda f: int(os.path.splitext(os.path.basename(f))[0].split('_')[-1])
    )
    if len(chunk_files) != total_chunks:
        raise Exception(f"Expected {total_chunks} chunks, but found {len(chunk_files)}.")
    list_file = os.path.join(chunk_dir, "chunks.txt")
    with open(list_file, "w") as f:
        for cf in chunk_files:
            f.write(f"file '{os.path.abspath(cf)}'\n")
    output_video = os.path.join(chunk_dir, f"{video_id}_reassembled.mp4")
    ffmpeg_cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file,
        "-c", "copy", output_video
    ]
    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to reassemble video: {e}")
    return output_video

async def match_against_crawled(phashes, new_video_id):
    matches = []
    async with async_session() as session:
        stmt = text("SELECT video_id, uploaded_phashes FROM crawled_videos")
        result = await session.execute(stmt)
        for row in result.fetchall():
            crawled_id = row[0]
            crawled_phashes = row[1]
            similarity = compute_video_similarity(phashes, crawled_phashes)
            if similarity >= settings.SIMILARITY_THRESHOLD:
                matches.append({"crawled_video_id": crawled_id, "similarity": round(similarity, 2)})
    if matches:
        logger.info(f"match_against_crawled: Found match for {new_video_id}: {matches}")
    else:
        logger.info(f"match_against_crawled: No matches found for {new_video_id}.")
    return matches

async def match_against_uploaded(phashes, new_video_id):
    matches = []
    async with async_session() as session:
        stmt = text("SELECT video_id, uploaded_phashes FROM uploaded_videos")
        result = await session.execute(stmt)
        for row in result.fetchall():
            uploaded_id = row[0]
            uploaded_phashes = row[1]
            similarity = compute_video_similarity(phashes, uploaded_phashes)
            if similarity >= settings.SIMILARITY_THRESHOLD:
                matches.append({"uploaded_video_id": uploaded_id, "similarity": round(similarity, 2)})
    if matches:
        logger.info(f"match_against_uploaded: Found match for {new_video_id}: {matches}")
    else:
        logger.info(f"match_against_uploaded: No matches found for {new_video_id}.")
    return matches

async def process_chunks_and_match(video_id: str, total_chunks: int):
    try:
        reassembled = reassemble_video(video_id, total_chunks)
    except Exception as e:
        logger.error(f"Error during reassembly for video_id {video_id}: {e}")
        return None
    pattern = os.path.join(settings.FRAMES_DIR, f"{video_id}_%d.jpg")
    frames = extract_keyframes(reassembled, pattern, fps=1)
    if not frames:
        logger.error(f"Failed to extract keyframes from reassembled video {video_id}")
        return None
    phashes = compute_phashes(frames)
    # For crawled videos, compare fingerprints against uploaded (content owner) videos.
    matches = await match_against_uploaded(phashes, video_id)
    flagged = True if matches else False

    async with async_session() as session:
        stmt = select(CrawledVideo).where(CrawledVideo.video_id == video_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.match_score = 0.0
            existing.uploaded_phashes = phashes
            existing.flagged = flagged
            session.add(existing)
        else:
            new_record = CrawledVideo(
                video_id=video_id,
                video_url="reassembled",
                match_score=0.0,
                uploaded_phashes=phashes,
                audio_spectrum=None,
                flagged=flagged
            )
            session.add(new_record)
        await session.commit()

    try:
        os.remove(reassembled)
    except Exception:
        pass
    cleanup_files(frames)
    result = {
        "video_id": video_id,
        "match_score": 0.0,
        "active_matches": matches,
        "uploaded_frames": len(phashes)
    }
    logger.info(f"Automatic match processing for video_id {video_id} complete with match score {result['match_score']}. Active matches: {matches}")
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
