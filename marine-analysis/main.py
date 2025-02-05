import os
import subprocess
import glob
import math
import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from fingerprint.video import extract_keyframes, compute_phashes
from fingerprint.audio import extract_audio, generate_audio_fingerprint
from storage.redis_utils import get_phashes, store_phashes
from config import settings
from db import async_session, Video, CrawledVideo, AnalyzedVideo, init_db
from sqlalchemy import select, text
from loguru import logger
from broadcaster import broadcaster

# --- Helper Functions ---

def hex_to_float_vector(hex_str: str) -> list:
    """
    Convert a hex string to a list of floats (each hex digit becomes 4 bits).
    """
    vector = []
    for ch in hex_str:
        n = int(ch, 16)
        bits = [(n >> i) & 1 for i in reversed(range(4))]
        vector.extend([float(bit) for bit in bits])
    return vector

def fix_vector_dimension(vector: list, target_dim: int = 64) -> list:
    """
    Ensure that a vector has exactly `target_dim` elements.
    If it is shorter, pad with 0.0. If longer, truncate.
    """
    if len(vector) < target_dim:
        return vector + [0.0] * (target_dim - len(vector))
    elif len(vector) > target_dim:
        return vector[:target_dim]
    return vector

def average_hash_vector(hex_list: list, target_dim: int = 64) -> list:
    """
    Compute the average vector from a list of hex strings.
    First, each hex string is converted to a float vector.
    Then, each vector is adjusted to have `target_dim` dimensions.
    Finally, the average (element-wise) is computed.
    """
    if not hex_list:
        return [0.0] * target_dim
    # Convert each hex string to a vector.
    vectors = [hex_to_float_vector(h) for h in hex_list]
    # Adjust each vector to the target dimension.
    vectors = [fix_vector_dimension(vec, target_dim) for vec in vectors]
    # Initialize the average vector.
    avg_vector = [0.0] * target_dim
    for vec in vectors:
        for i, val in enumerate(vec):
            avg_vector[i] += val
    count = len(vectors)
    avg_vector = [x / count for x in avg_vector]
    return avg_vector

def parse_db_vector(db_value):
    if db_value is None:
        return None
    if isinstance(db_value, list):
        return db_value
    if isinstance(db_value, str):
        try:
            return json.loads(db_value)
        except Exception as e:
            logger.error(f"Failed to parse DB vector as JSON: {e}")
            return None
    return None

def cosine_similarity(vec1: list, vec2: list) -> float:
    if not vec1 or not vec2:
        return 0.0
    try:
        dot = sum(a * b for a, b in zip(vec1, vec2))
    except Exception as e:
        logger.error(f"Error computing dot product: {e}")
        return 0.0
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return (dot / (norm1 * norm2)) * 100.0

def compute_video_similarity(uploaded_vector: list, reference_vector: list) -> float:
    return cosine_similarity(uploaded_vector, reference_vector)

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

# --- SSE Endpoint ---
@app.get("/sse")
async def sse(request: Request, user_email: str = Query(...)):
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

# --- /match-video Endpoint for User-Uploaded Videos ---
@app.post("/match-video")
async def match_video(
    video_file: UploadFile = File(...),
    user_email: str = Form(...),
    name: str = Form(...),
    description: str = Form(...)
):
    filename = video_file.filename
    custom_video_id = f"full_{filename}"
    temp_path = f"temp_{filename}"
    with open(temp_path, "wb") as f:
        f.write(await video_file.read())

    pattern = os.path.join(settings.FRAMES_DIR, f"uploaded_{filename}_%d.jpg")
    frames = None
    try:
        frames = extract_keyframes(temp_path, pattern, fps=1)
        if not frames:
            return JSONResponse(
                status_code=400,
                content={"error": "Failed to extract keyframes from uploaded video."}
            )
        phash_hex_list = compute_phashes(frames)
        # Compute average hash vector using target_dim 64 (to match db Vector(64))
        avg_vector = average_hash_vector(phash_hex_list, target_dim=64)
        # Ensure the vector has exactly 64 dimensions
        avg_vector = fix_vector_dimension(avg_vector, 64)

        # Extract audio fingerprint
        audio_file = "temp_audio.wav"
        try:
            extracted_audio = extract_audio(temp_path, audio_file)
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            extracted_audio = None
        audio_fp = generate_audio_fingerprint(extracted_audio) if extracted_audio else None

        # Match against crawled videos (modified to retrieve id)
        match_results = await match_against_crawled(avg_vector, custom_video_id)
        flagged = True if match_results else False
        if match_results:
            aggregate_score = max(match["similarity"] for match in match_results)
        else:
            aggregate_score = 0.0

        # Save the uploaded video in the "videos" table
        async with async_session() as session:
            stmt = select(Video).where(Video.filename == custom_video_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.hash_vector = avg_vector
                existing.audio_spectrum = audio_fp
                existing.fingerprint = custom_video_id
                existing.user_email = user_email
                existing.title = name
                existing.description = description
                session.add(existing)
                video_record = existing
            else:
                new_record = Video(
                    user_email=user_email,
                    filename=custom_video_id,
                    title=name,
                    description=description,
                    fingerprint=custom_video_id,
                    hash_vector=avg_vector,
                    audio_spectrum=audio_fp
                )
                session.add(new_record)
                await session.commit()  # commit to get an ID
                await session.refresh(new_record)
                video_record = new_record

            await session.commit()

            # Insert analysis record for the uploaded video (analysis_type "uploaded")
            analysis = AnalyzedVideo(
                analysis_type="uploaded",
                uploaded_video_id=video_record.id,
                phash_vector=avg_vector,
                analysis_result={"match_results": match_results},
                match_score=aggregate_score,
                flagged=flagged
            )
            session.add(analysis)

            # For each match from crawled videos, create a "comparison" record
            for match in match_results:
                comparison = AnalyzedVideo(
                    analysis_type="comparison",
                    uploaded_video_id=video_record.id,
                    crawled_video_id=match["crawled_video_id"],
                    phash_vector=avg_vector,
                    analysis_result=match,
                    match_score=match["similarity"],
                    flagged=flagged
                )
                session.add(comparison)
            await session.commit()

        ai_response = {
            "match_score": aggregate_score,
            "computed_hash": custom_video_id,
            "video_metadata": {
                "title": name,
                "description": description,
                "user_email": user_email,
                "active_matches": match_results,
                "flagged": flagged
            }
        }

        status_message = f"Video '{filename}' processed. Flagged: {flagged}. Matches: {match_results}"
        await broadcaster.broadcast(user_email, status_message)

        return JSONResponse(content=ai_response)
    except Exception as e:
        logger.error(f"Error in /match-video: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during video analysis."
        )
    finally:
        cleanup_files([temp_path])
        if frames:
            cleanup_files(frames)

# --- Setup for Video Chunk Storage ---
CHUNKS_DIR = os.path.join(os.getcwd(), "video_chunks")
if not os.path.exists(CHUNKS_DIR):
    os.makedirs(CHUNKS_DIR)

# ---
# IMPORTANT: BackgroundTasks in FastAPI expect synchronous callables.
# Since process_chunks_and_match is async, we wrap it in a sync function.
def schedule_process_chunks_and_match(video_id: str, total_chunks: int):
    asyncio.create_task(process_chunks_and_match(video_id, total_chunks))

@app.post("/upload-video-chunk")
async def upload_video_chunk(
    background_tasks: BackgroundTasks,
    video_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    video_chunk: UploadFile = File(...),
):
    chunk_dir = os.path.join(CHUNKS_DIR, video_id)
    if not os.path.exists(chunk_dir):
        os.makedirs(chunk_dir)
    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}.mp4")
    with open(chunk_path, "wb") as f:
        f.write(await video_chunk.read())
    existing_chunks = glob.glob(os.path.join(chunk_dir, "chunk_*.mp4"))
    if len(existing_chunks) == total_chunks:
        # Schedule the async processing function via the sync wrapper.
        background_tasks.add_task(schedule_process_chunks_and_match, video_id, total_chunks)
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
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
        "-c", "copy", output_video
    ]
    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to reassemble video: {e}")
    return output_video

# --- Matching Helper Functions (Modified to include the id field) ---
async def match_against_crawled(uploaded_vector: list, new_video_id: str):
    matches = []
    async with async_session() as session:
        # Now fetching id, video_url and hash_vector
        stmt = text("SELECT id, video_url, hash_vector FROM crawled_videos")
        result = await session.execute(stmt)
        for row in result.fetchall():
            crawled_video_id = row[0]
            # row[1] is video_url (if needed) and row[2] is hash_vector
            crawled_hash_vector = parse_db_vector(row[2])
            if not crawled_hash_vector:
                continue
            similarity = compute_video_similarity(uploaded_vector, crawled_hash_vector)
            if similarity >= settings.SIMILARITY_THRESHOLD:
                matches.append({
                    "crawled_video_id": crawled_video_id,
                    "video_url": row[1],
                    "similarity": round(similarity, 2)
                })
    if matches:
        logger.info(f"match_against_crawled: Found match for {new_video_id}: {matches}")
    else:
        logger.info(f"match_against_crawled: No matches found for {new_video_id}.")
    return matches

async def match_against_uploaded(uploaded_vector: list, new_video_id: str):
    matches = []
    async with async_session() as session:
        stmt = text("SELECT id, filename, hash_vector FROM videos")
        result = await session.execute(stmt)
        for row in result.fetchall():
            uploaded_video_id = row[0]
            uploaded_hash_vector = parse_db_vector(row[2])
            if not uploaded_hash_vector:
                continue
            similarity = compute_video_similarity(uploaded_vector, uploaded_hash_vector)
            if similarity >= settings.SIMILARITY_THRESHOLD:
                matches.append({
                    "uploaded_video_id": uploaded_video_id,
                    "filename": row[1],
                    "similarity": round(similarity, 2)
                })
    if matches:
        logger.info(f"match_against_uploaded: Found match for {new_video_id}: {matches}")
    else:
        logger.info(f"match_against_uploaded: No matches found for {new_video_id}.")
    return matches

# --- Process Chunks, Analyze and Save Crawled Video and Comparison Analysis ---
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

    phash_hex_list = compute_phashes(frames)
    # Compute average hash vector using target_dim 64 (to match db Vector(64))
    avg_vector = average_hash_vector(phash_hex_list, target_dim=64)
    avg_vector = fix_vector_dimension(avg_vector, 64)

    matches = await match_against_uploaded(avg_vector, video_id)
    flagged = True if matches else False
    if matches:
        aggregate_score = max(match["similarity"] for match in matches)
    else:
        aggregate_score = 0.0

    async with async_session() as session:
        stmt = select(CrawledVideo).where(CrawledVideo.video_url == video_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.hash_vector = avg_vector
            session.add(existing)
            crawled_record = existing
        else:
            new_record = CrawledVideo(
                video_url=video_id,
                title="reassembled",
                description="",
                video_metadata=None,
                hash_vector=avg_vector,
                audio_spectrum=None
            )
            session.add(new_record)
            await session.commit()
            await session.refresh(new_record)
            crawled_record = new_record
        await session.commit()

        analysis = AnalyzedVideo(
            analysis_type="crawled",
            crawled_video_id=crawled_record.id,
            phash_vector=avg_vector,
            analysis_result={"match_results": matches},
            match_score=aggregate_score,
            flagged=flagged
        )
        session.add(analysis)

        for match in matches:
            comparison = AnalyzedVideo(
                analysis_type="comparison",
                crawled_video_id=crawled_record.id,
                uploaded_video_id=match["uploaded_video_id"],
                phash_vector=avg_vector,
                analysis_result=match,
                match_score=match["similarity"],
                flagged=flagged
            )
            session.add(comparison)
        await session.commit()

    try:
        os.remove(reassembled)
    except Exception:
        pass
    cleanup_files(frames)

    result_data = {
        "video_id": video_id,
        "match_score": aggregate_score,
        "active_matches": matches,
        "uploaded_frames": len(phash_hex_list)
    }
    logger.info(
        f"Automatic match processing for video_id {video_id} complete with match score {result_data['match_score']}. Active matches: {matches}"
    )
    return result_data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
