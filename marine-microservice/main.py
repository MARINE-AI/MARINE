import os
import subprocess
import glob
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

from fingerprint.video import extract_keyframes, compute_phashes, compute_video_similarity
from fingerprint.audio import extract_audio, generate_audio_fingerprint
from storage.redis_utils import get_phashes, store_phashes
from config import (
    REFERENCE_VIDEO,
    REFERENCE_REDIS_KEY,
    FRAMES_DIR,
    SIMILARITY_THRESHOLD,
    KAFKA_BROKER,
    KAFKA_TOPIC
)
from db import async_session, VideoFingerprint, init_db

app = FastAPI()

def cleanup_files(file_list: list):
    for file_path in file_list:
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Warning: Failed to remove file {file_path}: {e}")

@app.on_event("startup")
async def startup_event():
    await init_db()
    if not os.path.exists(FRAMES_DIR):
        os.makedirs(FRAMES_DIR)

@app.post("/upload-reference")
async def upload_reference_video(video_file: UploadFile = File(...)):
    reference_video_path = f"reference_{video_file.filename}"
    with open(reference_video_path, "wb") as f:
        f.write(await video_file.read())

    reference_pattern = os.path.join(FRAMES_DIR, "reference_%d.jpg")
    try:
        reference_frames = extract_keyframes(reference_video_path, reference_pattern, fps=1)
        if not reference_frames:
            return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from reference video."})
        reference_phashes = compute_phashes(reference_frames)
        store_phashes(REFERENCE_REDIS_KEY, reference_phashes)
    finally:
        cleanup_files([reference_video_path])
        cleanup_files(reference_frames)
    
    return JSONResponse(content={"message": "Reference video uploaded and processed successfully!"})

@app.post("/match-video")
async def match_video(video_file: UploadFile = File(...)):
    uploaded_video_path = f"temp_{video_file.filename}"
    with open(uploaded_video_path, "wb") as f:
        f.write(await video_file.read())

    uploaded_pattern = os.path.join(FRAMES_DIR, f"uploaded_{video_file.filename}_%d.jpg")
    try:
        uploaded_frames = extract_keyframes(uploaded_video_path, uploaded_pattern, fps=1)
        if not uploaded_frames:
            return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from uploaded video."})
        uploaded_phashes = compute_phashes(uploaded_frames)
        audio_file = "temp_audio.wav"
        extracted_audio = extract_audio(uploaded_video_path, audio_file)
        audio_fingerprint = generate_audio_fingerprint(extracted_audio) if extracted_audio else None
        
        match_results = await active_video_matching(uploaded_phashes, video_file.filename, "full")
        
        reference_phashes = get_phashes(REFERENCE_REDIS_KEY)
        if not reference_phashes:
            raise HTTPException(status_code=400, detail="Reference video hashes not found. Upload a reference video first.")
        overall_similarity = compute_video_similarity(uploaded_phashes, reference_phashes)
        response = {
            "match_score": round(overall_similarity, 2),
            "active_matches": match_results,
            "metadata": {
                "uploaded_frames": len(uploaded_phashes),
                "reference_frames": len(reference_phashes)
            }
        }
        async with async_session() as session:
            vf = VideoFingerprint(
                video_id="full_" + video_file.filename,
                video_url="uploaded",
                match_score=round(overall_similarity, 2),
                uploaded_phashes=uploaded_phashes,
                audio_spectrum=audio_fingerprint,
                flagged=True if match_results else False
            )
            session.add(vf)
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

def reassemble_video(video_id: str, total_chunks: int) -> str:
    chunk_dir = os.path.join(CHUNKS_DIR, video_id)
    if not os.path.exists(chunk_dir):
        raise Exception("No chunks found for this video_id.")
    
    chunk_files = sorted(glob.glob(os.path.join(chunk_dir, "chunk_*.mp4")),
                         key=lambda f: int(os.path.splitext(os.path.basename(f))[0].split('_')[-1]))
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
        result = await session.execute("SELECT video_id, uploaded_phashes FROM video_fingerprints WHERE video_id != :new_id", {"new_id": new_video_id})
        stored_videos = result.fetchall()
        for row in stored_videos:
            stored_video_id = row[0]
            stored_phashes = row[1]
            similarity = compute_video_similarity(new_phashes, stored_phashes)
            if similarity >= SIMILARITY_THRESHOLD:
                matches.append({"stored_video_id": stored_video_id, "similarity": round(similarity, 2)})
    if matches:
        print(f"Active match for video {new_video_id}: {matches}")
    return matches

async def process_chunks_and_match(video_id: str, total_chunks: int):
    try:
        reassembled_video = reassemble_video(video_id, total_chunks)
    except Exception as e:
        print(f"Error during reassembly for video_id {video_id}: {e}")
        return

    output_pattern = os.path.join(FRAMES_DIR, f"{video_id}_%d.jpg")
    frames = extract_keyframes(reassembled_video, output_pattern, fps=1)
    if not frames:
        print(f"Failed to extract keyframes from reassembled video {video_id}")
        return
    
    uploaded_phashes = compute_phashes(frames)
    # audio_file = "temp_audio.wav"
    # extracted_audio = extract_audio(reassembled_video, audio_file)
    # audio_fingerprint = generate_audio_fingerprint(extracted_audio) if extracted_audio else None
    
    reference_phashes = get_phashes(REFERENCE_REDIS_KEY)
    if not reference_phashes:
        print("Reference video hashes not found. Upload a reference video first.")
        return
    
    overall_similarity = compute_video_similarity(uploaded_phashes, reference_phashes)
    active_matches = await active_video_matching(uploaded_phashes, video_id, "reassembled")
    
    async with async_session() as session:
        vf = VideoFingerprint(
            video_id=video_id,
            video_url="reassembled",
            match_score=round(overall_similarity, 2),
            uploaded_phashes=uploaded_phashes,
            audio_spectrum=None,
            flagged=True if active_matches else False
        )
        session.add(vf)
        await session.commit()
    
    try:
        os.remove(reassembled_video)
    except Exception:
        pass
    cleanup_files(frames)
    print(f"Automatic match processing for video_id {video_id} complete with match score {round(overall_similarity,2)}. Active matches: {active_matches}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
