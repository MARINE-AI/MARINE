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

from storage.redis_utils import get_phashes, store_phashes
from config import settings
from db import async_session, UploadedVideo, CrawledVideo, init_db
from sqlalchemy import text

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
    if not os.path.exists(settings.FRAMES_DIR):
        os.makedirs(settings.FRAMES_DIR)
        logger.info(f"Created frames directory: {settings.FRAMES_DIR}")
    yield
    logger.info("Shutting down application...")
    # Insert any shutdown logic if needed.
    logger.info("Shutdown complete.")

app = FastAPI(lifespan=lifespan, title="Video AI Microservice")

@app.post("/match-video")
async def match_video(video_file: UploadFile = File(...)):
    uploaded_video_path = f"temp_{video_file.filename}"
    with open(uploaded_video_path, "wb") as f:
        f.write(await video_file.read())

    uploaded_pattern = os.path.join(settings.FRAMES_DIR, f"uploaded_{video_file.filename}_%d.jpg")
    try:
        uploaded_frames = extract_keyframes(uploaded_video_path, uploaded_pattern, fps=1)
        if not uploaded_frames:
            return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from uploaded video."})
        uploaded_phashes = compute_phashes(uploaded_frames)
        audio_file = "temp_audio.wav"
        extracted_audio = extract_audio(uploaded_video_path, audio_file)
        audio_fingerprint = generate_audio_fingerprint(extracted_audio) if extracted_audio else None

        match_results = await active_video_matching(uploaded_phashes, video_file.filename, "full")

        reference_phashes = get_phashes(settings.REFERENCE_REDIS_KEY)
        if reference_phashes:
            overall_similarity = compute_video_similarity(uploaded_phashes, reference_phashes)
        else:
            overall_similarity = 0.0

        response = {
            "match_score": round(overall_similarity, 2),
            "active_matches": match_results,
            "metadata": {
                "uploaded_frames": len(uploaded_phashes),
                "reference_frames": len(reference_phashes) if reference_phashes else 0
            }
        }
        async with async_session() as session:
            record = UploadedVideo(
                video_id="full_" + video_file.filename,
                video_url="uploaded",
                match_score=round(overall_similarity, 2),
                uploaded_phashes=uploaded_phashes,
                audio_spectrum=audio_fingerprint,
                flagged=True if match_results else False
            )
            session.add(record)
            await session.commit()
    finally:
        cleanup_files([uploaded_video_path])
        cleanup_files(uploaded_frames)
    
    return JSONResponse(content=response)

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
    video_chunk_dir = os.path.join(CHUNKS_DIR, video_id)
    if not os.path.exists(video_chunk_dir):
        os.makedirs(video_chunk_dir)
    
    chunk_path = os.path.join(video_chunk_dir, f"chunk_{chunk_index}.mp4")
    with open(chunk_path, "wb") as f:
        f.write(await video_chunk.read())
    
    uploaded_chunks = glob.glob(os.path.join(video_chunk_dir, "chunk_*.mp4"))
    if len(uploaded_chunks) == total_chunks:
        background_tasks.add_task(process_chunks_and_match, video_id, total_chunks)
    
    return JSONResponse(content={"message": f"Chunk {chunk_index} for video {video_id} uploaded successfully."})

@app.post("/analyze")
async def analyze(video_id: str = Form(...), total_chunks: int = Form(...)):
    result = await process_chunks_and_match(video_id, total_chunks)
    if result is None:
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
        for chunk in chunk_files:
            f.write(f"file '{os.path.abspath(chunk)}'\n")
    
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

async def active_video_matching(new_phashes, new_video_id, new_video_url):
    matches = []
    async with async_session() as session:
        stmt = text("SELECT video_id, uploaded_phashes FROM uploaded_videos WHERE video_id LIKE :prefix")
        result = await session.execute(stmt, {"prefix": "full_%"})
        stored_videos = result.fetchall()
        for row in stored_videos:
            stored_video_id = row[0]
            stored_phashes = row[1]
            similarity = compute_video_similarity(new_phashes, stored_phashes)
            if similarity >= settings.SIMILARITY_THRESHOLD:
                matches.append({"stored_video_id": stored_video_id, "similarity": round(similarity, 2)})
    if matches:
        logger.info(f"Active match for video {new_video_id}: {matches}")
    return matches

async def process_chunks_and_match(video_id: str, total_chunks: int):
    try:
        reassembled_video = reassemble_video(video_id, total_chunks)
    except Exception as e:
        logger.error(f"Error during reassembly for video_id {video_id}: {e}")
        return None

    output_pattern = os.path.join(settings.FRAMES_DIR, f"{video_id}_%d.jpg")
    frames = extract_keyframes(reassembled_video, output_pattern, fps=1)
    if not frames:
        logger.error(f"Failed to extract keyframes from reassembled video {video_id}")
        return None
    
    uploaded_phashes = compute_phashes(frames)
    
    reference_phashes = get_phashes(settings.REFERENCE_REDIS_KEY)
    if not reference_phashes:
        logger.error("Not pirated.")
        return None

    overall_similarity = compute_video_similarity(uploaded_phashes, reference_phashes)
    active_matches = await active_video_matching(uploaded_phashes, video_id, "reassembled")

    async with async_session() as session:
        cv = CrawledVideo(
            video_id=video_id,
            video_url="reassembled",
            match_score=round(overall_similarity, 2),
            uploaded_phashes=uploaded_phashes,
            audio_spectrum=None,
            flagged=True if active_matches else False
        )
        session.add(cv)
        await session.commit()
    
    try:
        os.remove(reassembled_video)
    except Exception:
        pass
    cleanup_files(frames)
    
    result = {
        "video_id": video_id,
        "match_score": round(overall_similarity, 2),
        "active_matches": active_matches,
        "uploaded_frames": len(uploaded_phashes),
        "reference_frames": len(reference_phashes)
    }
    logger.info(f"Automatic match processing for video_id {video_id} complete with match score {result['match_score']}. Active matches: {active_matches}")
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
