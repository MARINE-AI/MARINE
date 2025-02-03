import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Kafka Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "piracy_links")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "piracy_detector")

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Playwright Configuration
HEADLESS = os.getenv("HEADLESS", "True").lower() == "true"

# Web Scraping Settings
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

# FastAPI Settings
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", 8000))
