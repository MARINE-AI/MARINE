import redis
import json
from config import settings

# Initialize the Redis client using settings.
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True  # This makes Redis return strings instead of bytes.
)

def store_phashes(key: str, phashes: list):
    """
    Stores a list of pHashes (converted to strings) in Redis under the given key.
    """
    phash_strs = [str(ph) for ph in phashes]
    redis_client.set(key, json.dumps(phash_strs))

def get_phashes(key: str) -> list:
    """
    Retrieves the list of pHashes stored in Redis under the given key.
    Converts them back to imagehash objects.
    """
    data = redis_client.get(key)
    if not data:
        return []
    phash_strs = json.loads(data)
    import imagehash
    return [imagehash.hex_to_hash(ph_str) for ph_str in phash_strs]
