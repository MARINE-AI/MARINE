import os
import subprocess
import glob
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

from fingerprint.video import extract_keyframes, compute_phashes, compute_video_similarity
from fingerprint.audio import extract_audio, generate_audio_fingerprint

from config import settings
from db import async_session, UploadedVideo, CrawledVideo, init_db
from sqlalchemy import select, text

from loguru import logger

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
    frames_dir = settings.FRAMES_DIR
    if not os.path.exists(frames_dir):
        os.makedirs(frames_dir)
        logger.info(f"Created frames directory: {frames_dir}")
    yield
    logger.info("Shutting down application...")
    logger.info("Shutdown complete.")

app = FastAPI(lifespan=lifespan, title="Video AI Microservice")

@app.post("/match-video")
async def match_video(video_file: UploadFile = File(...)):
    filename = video_file.filename
    video_id = f"full_{filename}"
    temp_path = f"temp_{filename}"

    with open(temp_path, "wb") as f:
        f.write(await video_file.read())

    frames_dir = settings.FRAMES_DIR
    pattern = os.path.join(frames_dir, f"uploaded_{filename}_%d.jpg")
    try:
        frames = extract_keyframes(temp_path, pattern, fps=1)
        if not frames:
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to extract keyframes from uploaded video."}
            )
        phashes = compute_phashes(frames)

        audio_file = "temp_audio.wav"
        extracted_audio = extract_audio(temp_path, audio_file)
        audio_fp = generate_audio_fingerprint(extracted_audio) if extracted_audio else None

        async with async_session() as session:
            stmt = select(UploadedVideo).where(UploadedVideo.video_id == video_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            matches = await match_against_crawled(phashes, video_id)

            flagged = True if matches else False

            if existing:
                existing.match_score = 0.0
                existing.uploaded_phashes = phashes
                existing.audio_spectrum = audio_fp
                existing.flagged = flagged
                session.add(existing)
            else:
                new_record = UploadedVideo(
                    video_id=video_id,
                    video_url="uploaded",
                    match_score=0.0,
                    uploaded_phashes=phashes,
                    audio_spectrum=audio_fp,
                    flagged=flagged
                )
                session.add(new_record)

            await session.commit()

        return JSONResponse(content={
            "video_id": video_id,
            "flagged": flagged,
            "matches": matches
        })

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

async def match_against_crawled(phashes, new_video_id):
    matches = []
    async with async_session() as session:
        stmt = text("SELECT video_id, uploaded_phashes FROM crawled_videos")
        rows = await session.execute(stmt)
        for row in rows:
            crawled_id = row[0]
            crawled_phashes = row[1]
            sim = compute_video_similarity(phashes, crawled_phashes)
            if sim >= settings.SIMILARITY_THRESHOLD:
                matches.append({
                    "crawled_video_id": crawled_id,
                    "similarity": round(sim, 2)
                })
    if matches:
        logger.info(f"match_against_crawled: Found match for {new_video_id}: {matches}")
    else:
        logger.info(f"match_against_crawled: No matches found for {new_video_id}.")
    return matches

async def match_against_uploaded(phashes, new_video_id):
    matches = []
    async with async_session() as session:
        stmt = text("SELECT video_id, uploaded_phashes FROM uploaded_videos")
        rows = await session.execute(stmt)
        for row in rows:
            uploaded_id = row[0]
            uploaded_hashes = row[1]
            sim = compute_video_similarity(phashes, uploaded_hashes)
            if sim >= settings.SIMILARITY_THRESHOLD:
                matches.append({
                    "uploaded_video_id": uploaded_id,
                    "similarity": round(sim, 2)
                })
    if matches:
        logger.info(f"match_against_uploaded: Found match for {new_video_id}: {matches}")
    else:
        logger.info(f"match_against_uploaded: No matches found for {new_video_id}.")
    return matches

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

async def process_chunks_and_match(video_id: str, total_chunks: int):
    try:
        reassembled = reassemble_video(video_id, total_chunks)
    except Exception as e:
        logger.error(f"Error during reassembly for {video_id}: {e}")
        return None

    pattern = os.path.join(settings.FRAMES_DIR, f"{video_id}_%d.jpg")
    frames = extract_keyframes(reassembled, pattern, fps=1)
    if not frames:
        logger.error(f"No frames extracted for {video_id}")
        return None

    phashes = compute_phashes(frames)
    # audio_file = "temp_audio.wav"
    # extracted_audio = extract_audio(reassembled, audio_file)
    # audio_fp = generate_audio_fingerprint(extracted_audio) if extracted_audio else None

    matches = await match_against_uploaded(phashes, video_id)

    flagged = True if matches else False

    async with async_session() as session:
        stmt = select(CrawledVideo).where(CrawledVideo.video_id == video_id)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.match_score = 0.0
            existing.uploaded_phashes = phashes
            existing.flagged = flagged
            session.add(existing)
        else:
            new_crawled = CrawledVideo(
                video_id=video_id,
                video_url="reassembled",
                match_score=0.0,
                uploaded_phashes=phashes,
                audio_spectrum=None,
                flagged=flagged
            )
            session.add(new_crawled)
        await session.commit()

    try:
        os.remove(reassembled)
    except:
        pass
    cleanup_files(frames)

    logger.info(f"Crawled video {video_id} reassembled & processed. Flagged: {flagged}, Matches: {matches}")
    return {
        "video_id": video_id,
        "flagged": flagged,
        "matches": matches
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
