import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from kafka import KafkaProducer

from fingerprint.video import extract_keyframes, compute_phashes, compute_video_similarity
from storage.redis_utils import get_phashes, store_phashes
from config import (
    REFERENCE_VIDEO,
    REFERENCE_REDIS_KEY,
    FRAMES_DIR,
    SIMILARITY_THRESHOLD,
    KAFKA_BROKER,
    KAFKA_TOPIC
)

app = FastAPI()
producer = KafkaProducer(bootstrap_servers=KAFKA_BROKER)

def send_message(message: str):
    """
    Sends a message to the Kafka topic.
    """
    try:
        producer.send(KAFKA_TOPIC, message.encode("utf-8"))
        producer.flush()
        print(f"Kafka message sent: {message}")
    except Exception as e:
        print(f"Error sending Kafka message: {e}")

def cleanup_files(file_list: list):
    for file_path in file_list:
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to remove file {file_path}: {e}")

@app.post("/upload-reference")
async def upload_reference_video(video_file: UploadFile = File(...)):
    """
    Accepts an uploaded reference video, extracts keyframes, computes pHashes,
    and stores them in Redis for future comparisons.
    """
    # Save the uploaded reference video temporarily.
    reference_video_path = f"reference_{video_file.filename}"
    with open(reference_video_path, "wb") as f:
        f.write(await video_file.read())

    # Define output pattern for keyframes of the reference video.
    reference_pattern = os.path.join(FRAMES_DIR, "reference_%d.jpg")
    
    try:
        # Extract keyframes from the reference video.
        reference_frames = extract_keyframes(reference_video_path, reference_pattern, fps=1)
        if not reference_frames:
            return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from reference video."})
        
        # Compute pHashes for the reference frames.
        reference_phashes = compute_phashes(reference_frames)
        # Store the computed pHashes in Redis.
        store_phashes(REFERENCE_REDIS_KEY, reference_phashes)
    finally:
        # Cleanup temporary files.
        cleanup_files([reference_video_path])
        cleanup_files(reference_frames)
    
    return JSONResponse(content={"message": "Reference video uploaded and processed successfully!"})

@app.post("/match-video")
async def match_video(video_file: UploadFile = File(...)):
    """
    Accepts an uploaded video, extracts keyframes, computes pHashes,
    compares them to a reference video, and sends a Kafka alert if matched.
    """
    # Save the uploaded video temporarily.
    uploaded_video_path = f"temp_{video_file.filename}"
    with open(uploaded_video_path, "wb") as f:
        f.write(await video_file.read())

    # Define output pattern for keyframes of the uploaded video.
    uploaded_pattern = os.path.join(FRAMES_DIR, f"uploaded_{video_file.filename}_%d.jpg")
    
    try:
        # Extract keyframes from the uploaded video.
        uploaded_frames = extract_keyframes(uploaded_video_path, uploaded_pattern, fps=1)
        if not uploaded_frames:
            return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from uploaded video."})
        
        # Compute pHashes for uploaded frames.
        uploaded_phashes = compute_phashes(uploaded_frames)
        
        # Retrieve reference pHashes from Redis.
        reference_phashes = get_phashes(REFERENCE_REDIS_KEY)
        if not reference_phashes:
            # If no reference pHashes are in Redis, try to use the local reference video.
            if not os.path.exists(REFERENCE_VIDEO):
                raise HTTPException(status_code=400, detail="Reference video not found.")
            
            reference_pattern = os.path.join(FRAMES_DIR, "reference_%d.jpg")
            reference_frames = extract_keyframes(REFERENCE_VIDEO, reference_pattern, fps=1)
            if not reference_frames:
                raise HTTPException(status_code=400, detail="Failed to extract keyframes from reference video.")
            
            reference_phashes = compute_phashes(reference_frames)
            store_phashes(REFERENCE_REDIS_KEY, reference_phashes)
            cleanup_files(reference_frames)
            return JSONResponse(status_code=400, content={"error": "Failed to compute hashes for reference video frames."})
        
        # Compute overall similarity.
        overall_similarity = compute_video_similarity(uploaded_phashes, reference_phashes)
        
        # Check against threshold and send Kafka message if needed.
        kafka_message = None
        if overall_similarity >= SIMILARITY_THRESHOLD:
            video_id = 0  # Placeholder; replace with actual video ID if available.
            piracy_url = f"https://example.com/pirated/{video_file.filename}"
            kafka_message = f"PiracyFound:{video_id}:{piracy_url}:{round(overall_similarity, 2)}"
            send_message(kafka_message)
        
        # Prepare response payload.
        response = {
            "match_score": round(overall_similarity, 2),
            "metadata": {
                "uploaded_frames": len(uploaded_phashes),
                "reference_frames": len(reference_phashes)
            }
        }
        if kafka_message:
            response["kafka_message"] = kafka_message

    finally:
        # Cleanup temporary files.
        cleanup_files([uploaded_video_path])
        cleanup_files(uploaded_frames)
    
    return JSONResponse(content=response)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
