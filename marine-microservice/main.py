import os
import ffmpeg
import numpy as np
import imagehash
from PIL import Image
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

# Function to extract a keyframe using FFmpeg
def extract_keyframe(video_path, output_image="frame.jpg"):
    (
        ffmpeg.input(video_path, ss=1)  # Extract frame at 1 second
        .output(output_image, vframes=1, format="image2", vcodec="mjpeg")
        .overwrite_output()
        .run(quiet=True)
    )
    return output_image

# Function to compute pHash
def compute_phash(image_path):
    image = Image.open(image_path)
    return imagehash.phash(image)

# Hamming Distance Function
def hamming_distance(hash1, hash2):
    return hash1 - hash2  # Computes bitwise Hamming distance

@app.post("/compare-videos")
async def compare_videos(video1: UploadFile = File(...), video2: UploadFile = File(...)):
    """
    Accepts two videos, extracts keyframes, computes pHash, and compares them.
    """
    # Save videos temporarily
    video1_path = f"temp_{video1.filename}"
    video2_path = f"temp_{video2.filename}"

    with open(video1_path, "wb") as f:
        f.write(await video1.read())
    with open(video2_path, "wb") as f:
        f.write(await video2.read())

    # Extract keyframes
    keyframe1_path = extract_keyframe(video1_path, "frame1.jpg")
    keyframe2_path = extract_keyframe(video2_path, "frame2.jpg")

    # Compute perceptual hashes
    hash1 = compute_phash(keyframe1_path)
    hash2 = compute_phash(keyframe2_path)

    # Compute similarity score
    distance = hamming_distance(hash1, hash2)
    similarity = 1 - (distance / 64)  # Normalize to [0,1] (pHash is 64-bit)

    # Cleanup temporary files
    os.remove(video1_path)
    os.remove(video2_path)
    os.remove(keyframe1_path)
    os.remove(keyframe2_path)

    return JSONResponse(content={
        "video1": video1.filename,
        "video2": video2.filename,
        "hamming_distance": distance,
        "similarity_score": round(similarity, 2)
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
