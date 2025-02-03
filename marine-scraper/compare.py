import os
import base64
import json
import imagehash
import requests
from io import BytesIO
from fastapi import APIRouter, HTTPException
from PIL import Image
import redis
import numpy as np
import faiss
from config import REDIS_URL

router = APIRouter()

redis_client = redis.from_url(REDIS_URL)

def compute_phash(image: Image.Image):
    return str(imagehash.phash(image))

@router.get("/compare")
async def compare_endpoint(image_url: str):
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading image: {str(e)}")

    candidate_phash = compute_phash(img)
    candidate_hash_obj = imagehash.hex_to_hash(candidate_phash)

    # Retrieve all stored video metadata keys.
    keys = redis_client.keys("video:*")
    if not keys:
        return {"error": "No video metadata found in Redis."}

    best_match = None
    best_distance = None
    embeddings_list = []
    metadata_list = []
    phash_list = []

    for key in keys:
        data = redis_client.get(key)
        if data:
            metadata = json.loads(data)
            rep_hash = metadata.get("phashes", [None])[0]
            if rep_hash:
                distance = candidate_hash_obj - imagehash.hex_to_hash(rep_hash)
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_match = metadata
            # If deep embeddings are stored, collect them for FAISS search.
            if metadata.get("representative_embedding"):
                embeddings_list.append(np.array(metadata["representative_embedding"], dtype=np.float32))
                metadata_list.append(metadata)
                phash_list.append(metadata.get("representative_hash"))

    if best_match is None:
        return {"error": "No match found by pHash."}

    # Use FAISS if we have multiple embeddings.
    if embeddings_list:
        embeddings_np = np.vstack(embeddings_list)
        dim = embeddings_np.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings_np)
        # Compute candidate deep embedding using MobileNetV2 similar to AI service,
        # Here we use candidate pHash image for simplicity.
        # In production, you might download the candidate video thumbnail and compute its deep embedding.
        # For this example, we reuse the pHash-based vector as a dummy deep embedding.
        candidate_embedding = np.random.rand(dim).astype("float32")  # Replace with real computation.
        distances, indices = index.search(np.array([candidate_embedding]), k=1)
        faiss_distance = distances[0][0]
        # Convert FAISS distance to a similarity score.
        similarity_faiss = max(0, 100 - (faiss_distance / 100.0 * 100))  # Adjust scaling as needed.
    else:
        similarity_faiss = None

    max_distance = 64
    similarity_phash = max(0, 100 - (best_distance / max_distance * 100))
    return {
        "candidate_phash": candidate_phash,
        "best_match": best_match,
        "similarity_phash": similarity_phash,
        "similarity_faiss": similarity_faiss
    }
