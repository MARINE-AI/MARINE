def hamming_similarity(hash1, hash2) -> float:
    distance = hash1 - hash2
    return 1 - (distance / 64.0)
