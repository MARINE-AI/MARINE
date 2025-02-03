# app/config.py

import os

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "4.240.103.202")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Kafka configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "4.240.103.202:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "piracy_links")

# Reference video settings
REFERENCE_VIDEO = os.getenv("REFERENCE_VIDEO", "reference_video.mp4")
REFERENCE_REDIS_KEY = os.getenv("REFERENCE_REDIS_KEY", "reference_video_phashes")

# Frame extraction settings
FRAMES_DIR = "frames_temp"
os.makedirs(FRAMES_DIR, exist_ok=True)

# Similarity threshold
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
