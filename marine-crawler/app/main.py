import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import uvicorn

from app.crawler import run_crawlers
from app.downloader import video_downloader_worker
from app.kafka_client import close_kafka_producer
from app.config import settings
from loguru import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    if not os.path.exists(settings.FRAMES_DIR):
        os.makedirs(settings.FRAMES_DIR)
        logger.info(f"Created frames directory: {settings.FRAMES_DIR}")
    downloader_task = asyncio.create_task(video_downloader_worker())
    logger.info("Video downloader worker launched.")
    
    yield
    
    logger.info("Shutting down application...")
    downloader_task.cancel()
    try:
        await downloader_task
    except asyncio.CancelledError:
        logger.info("Video downloader worker task cancelled.")
    await close_kafka_producer()
    logger.info("Shutdown complete.")

app = FastAPI(lifespan=lifespan, title="Video Crawler Microservice")

url_list = []

class URLRequest(BaseModel):
    url: str

@app.post("/submit")
async def submit_url(request: URLRequest):
    """
    Submits a URL for crawling.
    """
    url_list.append(request.url)
    return {"message": f"URL {request.url} submitted for crawling."}

@app.get("/start_crawling")
async def start_crawling():
    """
    Starts crawling for all submitted URLs.
    """
    if not url_list:
        raise HTTPException(status_code=400, detail="No URLs submitted.")
    urls_to_crawl = url_list.copy()
    url_list.clear()
    # Schedule the crawling tasks in the background.
    asyncio.create_task(run_crawlers(urls_to_crawl))
    return {"message": f"Started crawling {len(urls_to_crawl)} URLs."}

@app.on_event("shutdown")
async def shutdown_event():
    await close_kafka_producer()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=False)
