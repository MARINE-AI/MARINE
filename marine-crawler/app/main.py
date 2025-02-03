import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.crawler import run_crawlers
from app.downloader import video_downloader_worker
from app.kafka_client import close_kafka_producer
from loguru import logger
import uvicorn

app = FastAPI(title="Video Crawler Microservice")

url_list = []

class URLRequest(BaseModel):
    url: str

@app.post("/submit")
async def submit_url(request: URLRequest):
    url_list.append(request.url)
    return {"message": f"URL {request.url} submitted for crawling."}

@app.get("/start_crawling")
async def start_crawling():
    if not url_list:
        raise HTTPException(status_code=400, detail="No URLs submitted.")
    urls_to_crawl = url_list.copy()
    url_list.clear()
    asyncio.create_task(run_crawlers(urls_to_crawl))
    return {"message": f"Started crawling {len(urls_to_crawl)} URLs."}

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    loop.create_task(video_downloader_worker())
    logger.info("Video downloader worker started")

@app.on_event("shutdown")
async def shutdown_event():
    await close_kafka_producer()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=False)
