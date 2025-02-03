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

app = FastAPI()

redis_client = redis.Redis(host="4.240.103.202", port=6379, db=0, decode_responses=True)

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "localhost:9092")
producer = KafkaProducer(bootstrap_servers=KAFKA_BROKERS)

REFERENCE_VIDEO = "reference_video.mp4"
REFERENCE_REDIS_KEY = "reference_video_phashes"

# Directory for temporary frames
FRAMES_DIR = "frames_temp"
os.makedirs(FRAMES_DIR, exist_ok=True)

# --- Utility Functions ---

def extract_keyframes(video_path: str, output_pattern: str, fps: int = 1) -> list:
    """
    Extracts keyframes from the given video using ffmpeg.
    The output_pattern should contain a %d placeholder (e.g., "frames_temp/frame%d.jpg").
    Extracts 'fps' frames per second.
    
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
        print("FFmpeg error:", e)
        return []
    
    # Glob for all files matching the pattern (e.g., frames_temp/frame*.jpg)
    frame_files = sorted(glob.glob(output_pattern.replace("%d", "*")))
    return frame_files

def compute_phashes_for_frames(frame_paths: list) -> list:
    """
    Computes the perceptual hash (pHash) for each frame image.
    Returns a list of hash objects (or their string representations).
    """
    hashes = []
    for frame in frame_paths:
        try:
            img = Image.open(frame)
            ph = imagehash.phash(img)
            hashes.append(ph)
        except Exception as e:
            print(f"Error processing frame {frame}: {e}")
    return hashes

def hamming_similarity(hash1, hash2) -> float:
    """
    Computes normalized similarity from two imagehash objects.
    Returns a float between 0 and 1, where 1 indicates identical.
    """
    # pHash is 64-bit; maximum distance is 64.
    distance = hash1 - hash2
    return 1 - (distance / 64.0)

def store_phashes_in_redis(key: str, phashes: list):
    """
    Stores the list of pHashes (converted to strings) in Redis as a JSON array.
    """
    phash_strs = [str(ph) for ph in phashes]
    redis_client.set(key, json.dumps(phash_strs))

def get_phashes_from_redis(key: str) -> list:
    """
    Retrieves the list of pHashes (as imagehash objects) from Redis.
    Returns an empty list if not found.
    """
    data = redis_client.get(key)
    if not data:
        return []
    phash_strs = json.loads(data)
    # Convert each string back to an imagehash object (the default hash type is imagehash.ImageHash)
    return [imagehash.hex_to_hash(ph_str) for ph_str in phash_strs]

def cleanup_files(file_list: list):
    for file_path in file_list:
        try:
            os.remove(file_path)
        except Exception:
            pass

def compute_video_similarity(uploaded_hashes: list, reference_hashes: list) -> float:
    """
    For each hash in uploaded_hashes, find the maximum similarity with any of the reference_hashes.
    Then average these maximum similarities to get an overall score.
    """
    if not uploaded_hashes or not reference_hashes:
        return 0.0
    
    similarities = []
    for u_hash in uploaded_hashes:
        # Compute similarity with each reference hash and take the maximum.
        max_sim = max(hamming_similarity(u_hash, r_hash) for r_hash in reference_hashes)
        similarities.append(max_sim)
    # Average similarity over all frames.
    overall_similarity = sum(similarities) / len(similarities)
    return overall_similarity

# --- Endpoints ---

@app.post("/match-video")
async def match_video(video_file: UploadFile = File(...)):
    """
    Accepts an uploaded video, extracts multiple keyframes, computes pHashes,
    compares them to a local reference video's keyframes (from Redis or computed on the fly),
    and publishes a Kafka message if the similarity meets the threshold.
    """
    # Save the uploaded video temporarily.
    uploaded_video_path = f"temp_{video_file.filename}"
    with open(uploaded_video_path, "wb") as f:
        f.write(await video_file.read())
    
    # Define output pattern for keyframes from the uploaded video.
    uploaded_pattern = os.path.join(FRAMES_DIR, f"uploaded_{video_file.filename}_%d.jpg")
    
    try:
        # Extract keyframes from the uploaded video.
        uploaded_frames = extract_keyframes(uploaded_video_path, uploaded_pattern, fps=1)
        if not uploaded_frames:
            return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from uploaded video."})
        
        # Compute pHashes for uploaded frames.
        uploaded_phashes = compute_phashes_for_frames(uploaded_frames)
        
        # Check if reference video's pHashes are already in Redis.
        reference_phashes = get_phashes_from_redis(REFERENCE_REDIS_KEY)
        if not reference_phashes:
            # Extract keyframes from the reference video.
            if not os.path.exists(REFERENCE_VIDEO):
                return JSONResponse(status_code=400, content={"error": "Reference video not found."})
            
            reference_pattern = os.path.join(FRAMES_DIR, "reference_%d.jpg")
            reference_frames = extract_keyframes(REFERENCE_VIDEO, reference_pattern, fps=1)
            if not reference_frames:
                return JSONResponse(status_code=400, content={"error": "Failed to extract keyframes from reference video."})
            
            reference_phashes = compute_phashes_for_frames(reference_frames)
            # Store the reference pHashes in Redis.
            store_phashes_in_redis(REFERENCE_REDIS_KEY, reference_phashes)
            # Clean up extracted reference frames.
            cleanup_files(reference_frames)
        
        # Compute overall similarity between the uploaded video and the reference video.
        overall_similarity = compute_video_similarity(uploaded_phashes, reference_phashes)
        
        # Define a threshold for flagging piracy.
        threshold = 0.85
        kafka_message = None
        if overall_similarity >= threshold:
            # Prepare Kafka message.
            # (Video ID is unknown at this point; using 0 as a placeholder.)
            video_id = 0
            piracy_url = f"https://example.com/pirated/{video_file.filename}"
            kafka_message = f"PiracyFound:{video_id}:{piracy_url}:{round(overall_similarity, 2)}"
            producer.send("piracy_links", kafka_message.encode("utf-8"))
            producer.flush()
        
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
        # Cleanup: remove temporary video and uploaded frames.
        cleanup_files([uploaded_video_path])
        cleanup_files(uploaded_frames)
    
    return JSONResponse(content=response)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
