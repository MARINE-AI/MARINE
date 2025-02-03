import os
import json
import ffmpeg
import imagehash
from PIL import Image
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
import redis
from kafka import KafkaProducer
import glob
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

redis_client = redis.Redis(host="4.240.103.202", port=6379, db=0, decode_responses=True)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "4.240.103.202:9092")
producer = KafkaProducer(bootstrap_servers=KAFKA_BROKER)

REFERENCE_VIDEO = "reference_video.mp4"
REFERENCE_REDIS_KEY = "reference_video_phashes"

FRAMES_DIR = "frames_temp"
os.makedirs(FRAMES_DIR, exist_ok=True)

# --- Utility Functions ---

def extract_keyframes(video_path: str, output_pattern: str, fps: int = 1) -> list:
    """
    Extracts keyframes from the given video using ffmpeg.
    The output_pattern should contain a %d placeholder.
    Returns a list of file paths to the extracted frames.
    """
    try:
        (
            ffmpeg
            .input(video_path)
            .output(output_pattern, vf=f"fps={fps}", format="image2", vcodec="mjpeg")
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error for {video_path}: {e.stderr.decode() if e.stderr else e}")
        return []
    
    # Gather all files matching the pattern.
    frame_files = sorted(glob.glob(output_pattern.replace("%d", "*")))
    logger.info(f"Extracted {len(frame_files)} frames from {video_path}")
    return frame_files

def compute_phashes_for_frames(frame_paths: list) -> list:
    """
    Computes the perceptual hash (pHash) for each frame image.
    Returns a list of imagehash objects.
    """
    hashes = []
    for frame in frame_paths:
        try:
            img = Image.open(frame)
            ph = imagehash.phash(img)
            hashes.append(ph)
        except Exception as e:
            logger.error(f"Error processing frame {frame}: {e}")
    return hashes

def hamming_similarity(hash1, hash2) -> float:
    """
    Computes normalized similarity between two imagehash objects.
    Returns a float between 0 and 1 (1 means identical).
    """
    distance = hash1 - hash2  # pHash is 64-bit; max distance is 64.
    return 1 - (distance / 64.0)

def store_phashes_in_redis(key: str, phashes: list):
    """
    Stores the list of pHashes (as hex strings) in Redis as a JSON array.
    """
    phash_strs = [str(ph) for ph in phashes]
    redis_client.set(key, json.dumps(phash_strs))

def get_phashes_from_redis(key: str) -> list:
    """
    Retrieves the list of pHashes from Redis and converts them back to imagehash objects.
    Returns an empty list if not found or if the data is invalid.
    """
    data = redis_client.get(key)
    if not data:
        return []
    try:
        phash_strs = json.loads(data)
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from Redis for key: {key}.")
        return []
    return [imagehash.hex_to_hash(ph_str) for ph_str in phash_strs]

def cleanup_files(file_list: list):
    for file_path in file_list:
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to remove file {file_path}: {e}")

def compute_video_similarity(uploaded_hashes: list, reference_hashes: list) -> float:
    """
    For each uploaded hash, find the maximum similarity with any of the reference hashes.
    Returns the average of these maximum similarities.
    """
    if not uploaded_hashes or not reference_hashes:
        return 0.0
    similarities = []
    for u_hash in uploaded_hashes:
        max_sim = max(hamming_similarity(u_hash, r_hash) for r_hash in reference_hashes)
        similarities.append(max_sim)
    overall_similarity = sum(similarities) / len(similarities)
    return overall_similarity

# --- Endpoint ---

@app.post("/match-video")
async def match_video(video_file: UploadFile = File(...)):
    """
    Accepts an uploaded video file, extracts keyframes and computes perceptual hashes,
    compares them with the reference video, and (if above threshold) sends a Kafka message.
    """
    # Save the uploaded video temporarily.
    uploaded_video_path = f"temp_{video_file.filename}"
    try:
        content = await video_file.read()
        with open(uploaded_video_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Error saving uploaded video: {e}")
        return JSONResponse(status_code=400, content={"error": "Unable to save the uploaded video."})
    
    # Define the pattern for extracted frames from the uploaded video.
    uploaded_pattern = os.path.join(FRAMES_DIR, f"uploaded_{video_file.filename}_%d.jpg")
    uploaded_frames = extract_keyframes(uploaded_video_path, uploaded_pattern, fps=1)
    if not uploaded_frames:
        cleanup_files([uploaded_video_path])
        return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from uploaded video."})
    
    uploaded_phashes = compute_phashes_for_frames(uploaded_frames)
    if not uploaded_phashes:
        cleanup_files([uploaded_video_path])
        cleanup_files(uploaded_frames)
        return JSONResponse(status_code=400, content={"error": "Failed to compute hashes for uploaded video frames."})
    
    # Get or compute the reference video hashes.
    reference_phashes = get_phashes_from_redis(REFERENCE_REDIS_KEY)
    if not reference_phashes:
        if not os.path.exists(REFERENCE_VIDEO):
            cleanup_files([uploaded_video_path])
            cleanup_files(uploaded_frames)
            return JSONResponse(status_code=400, content={"error": "Reference video not found."})
        
        reference_pattern = os.path.join(FRAMES_DIR, "reference_%d.jpg")
        reference_frames = extract_keyframes(REFERENCE_VIDEO, reference_pattern, fps=1)
        if not reference_frames:
            cleanup_files([uploaded_video_path])
            cleanup_files(uploaded_frames)
            return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from reference video."})
        
        reference_phashes = compute_phashes_for_frames(reference_frames)
        if not reference_phashes:
            cleanup_files([uploaded_video_path])
            cleanup_files(uploaded_frames)
            cleanup_files(reference_frames)
            return JSONResponse(status_code=400, content={"error": "Failed to compute hashes for reference video frames."})
        
        store_phashes_in_redis(REFERENCE_REDIS_KEY, reference_phashes)
        cleanup_files(reference_frames)
    
    # Compute similarity score.
    overall_similarity = compute_video_similarity(uploaded_phashes, reference_phashes)
    
    # Define threshold for sending Kafka message.
    threshold = 0.85
    kafka_message = None
    if overall_similarity >= threshold:
        video_id = 0  # Placeholder; adjust as needed.
        piracy_url = f"https://example.com/pirated/{video_file.filename}"
        kafka_message = f"PiracyFound:{video_id}:{piracy_url}:{round(overall_similarity, 2)}"
        try:
            producer.send("piracy_links", kafka_message.encode("utf-8"))
            producer.flush()
        except Exception as e:
            logger.error(f"Error sending Kafka message: {e}")
    
    # Prepare the response payload.
    response = {
        "match_score": round(overall_similarity, 2),
        "metadata": {
            "uploaded_frames": len(uploaded_phashes),
            "reference_frames": len(reference_phashes)
        }
    }
    if kafka_message:
        response["kafka_message"] = kafka_message

    # Cleanup temporary files.
    cleanup_files([uploaded_video_path])
    cleanup_files(uploaded_frames)
    
    return JSONResponse(content=response)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
