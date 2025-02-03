import redis
import json
from config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

def store_phashes(key: str, phashes: list):
    phash_strs = [str(ph) for ph in phashes]
    redis_client.set(key, json.dumps(phash_strs))

def get_phashes(key: str) -> list:

    data = redis_client.get(key)
    if not data:
        return []
    phash_strs = json.loads(data)
    import imagehash
    return [imagehash.hex_to_hash(ph_str) for ph_str in phash_strs]
