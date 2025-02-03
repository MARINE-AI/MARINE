# app/fingerprinting/common.py

def hamming_similarity(hash1, hash2) -> float:
    """
    Computes normalized similarity from two imagehash objects.
    """
    # pHash is 64-bit; maximum distance is 64.
    distance = hash1 - hash2
    return 1 - (distance / 64.0)
    