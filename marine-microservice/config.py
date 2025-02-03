import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    REFERENCE_VIDEO: str = os.getenv("REFERENCE_VIDEO", "reference.mp4")
    REFERENCE_REDIS_KEY: str = os.getenv("REFERENCE_REDIS_KEY", "ref_phashes")
    FRAMES_DIR: str = os.getenv("FRAMES_DIR", "frames_temp")
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))
    KAFKA_BROKER: str = os.getenv("KAFKA_BROKER", "4.240.103.202:9092")
    KAFKA_TOPIC: str = os.getenv("KAFKA_TOPIC", "alerts")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "4.240.103.202")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    class Config:
        env_file = ".env"

settings = Settings()
