import os
import glob
import ffmpeg
from PIL import Image
import imagehash
from .common import hamming_similarity

def extract_keyframes(video_path: str, output_pattern: str, fps: int = 1) -> list:
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
    
    frame_files = sorted(glob.glob(output_pattern.replace("%d", "*")))
    return frame_files

def compute_phashes(frame_paths: list) -> list:
    hashes = []
    for frame in frame_paths:
        try:
            img = Image.open(frame)
            ph = imagehash.phash(img)
            hashes.append(ph)
        except Exception as e:
            print(f"Error processing frame {frame}: {e}")
    return [str(h) for h in hashes]

def compute_video_similarity(uploaded_hashes: list, reference_hashes: list) -> float:
    from .common import hamming_similarity
    if not uploaded_hashes or not reference_hashes:
        return 0.0

    similarities = []
    for u_hash in uploaded_hashes:
        from PIL import Image
        u = imagehash.hex_to_hash(u_hash)
        max_sim = max(hamming_similarity(u, imagehash.hex_to_hash(r_hash)) for r_hash in reference_hashes)
        similarities.append(max_sim)
    return sum(similarities) / len(similarities)
