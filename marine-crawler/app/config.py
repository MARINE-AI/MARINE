import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "4.240.103.202:9092")
    kafka_crawl_topic: str = os.getenv("KAFKA_CRAWL_TOPIC", "crawl-tasks")
    kafka_video_download_topic: str = os.getenv("KAFKA_VIDEO_DOWNLOAD_TOPIC", "video-download-tasks")
    kafka_video_chunks_topic: str = os.getenv("KAFKA_VIDEO_CHUNKS_TOPIC", "video-chunks")
    
    max_concurrent_crawlers: int = int(os.getenv("MAX_CONCURRENT_CRAWLERS", 100))
    user_agent: str = os.getenv(
        "USER_AGENT", 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    segment_duration: int = int(os.getenv("SEGMENT_DURATION", 10))
    
    downstream_endpoint: str = os.getenv("DOWNSTREAM_ENDPOINT", "http://localhost:8000/upload-reference")
    
    FRAMES_DIR: str = os.getenv("FRAMES_DIR", "frames")
    
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))

    class Config:
        env_file = ".env"

settings = Settings()
