import os
import subprocess
import json
import tempfile
import threading
import time
import argparse
import sys
import random
import asyncio

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn

import google.generativeai as genai
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import httpx

os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_TRACE"] = ""

# todo: replace with config.py implementation
genai.configure(api_key="")

app = FastAPI()

url_queue = asyncio.Queue()

def extract_keyframes(video_path: str, output_dir: str, frame_interval: int = 30) -> list:
    """
    Uses FFmpeg to extract keyframes from the provided video at the specified interval.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"select='not(mod(n\\,{frame_interval}))'",
        "-vsync", "vfr",
        os.path.join(output_dir, "keyframe_%04d.jpg")
    ]
    
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Collect the paths of the extracted keyframes
    keyframe_paths = []
    for file in sorted(os.listdir(output_dir)):
        if file.endswith(".jpg"):
            keyframe_paths.append(os.path.join(output_dir, file))
    return keyframe_paths

def clean_output(raw_text: str) -> str:
    """
    Cleans the output text by removing markdown code block formatting if present.
    """
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().endswith("```"):
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()
    return raw_text

def analyze_image_for_dork(image_path: str, description: str) -> list:
    """
    Uploads the image (a keyframe) to the Gemini API and returns a JSON array of Google dork queries.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Upload the image file to the Gemini API
    myfile = genai.upload_file(image_path)
    
    prompt = f"""
You are an advanced image analysis engine. Your task is to analyze the provided image (a keyframe extracted from a video)
and deduce the context, theme, and visual cues that could be used to locate related content on the web.
Based on your analysis, generate Google dork queries using specific keywords and search operators (such as site:, intext:, intitle:, etc.).
If it's a popular video, you can also use the title of the video to generate dork queries.

Instructions:
1. Analyze the image and extract key visual and contextual elements.
2. Construct one or more detailed Google dork query strings that incorporate these elements.
3. Return only a JSON array containing the Google dork query strings. Each element of the array must be a string.
4. Do not include any additional text, commentary, or extra fields.

Additional Context: {description}

Return only the JSON array.
"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    result = model.generate_content([myfile, "\n\n", prompt])
    
    # Remove any markdown formatting
    cleaned_text = clean_output(result.text)
    try:
        output_array = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from model output: {cleaned_text}") from e

    if not isinstance(output_array, list):
        raise ValueError("The model output is not a JSON array as expected.")

    return output_array

url_list = []

class URLRequest(BaseModel):
    url: str

@app.post("/submit")
async def submit_url(request: URLRequest):
    """
    /submit endpoint:
      - Receives a URL via POST and appends it to the global url_list.
    """
    url_list.append(request.url)
    print(f"[Submit] URL {request.url} submitted.")
    return {"message": f"URL {request.url} submitted for crawling."}

@app.post("/discover")
async def discover(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(""),
    description: str = Form("")
):
    """
    /discover endpoint:
      - Accepts a video file along with optional name and description.
      - Extracts keyframes from the video.
      - Sends each keyframe to the Gemini API to obtain Google dork queries.
      - Returns a JSON array of unique dork queries.
      - Immediately schedules background processing of these queries.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, file.filename)
            contents = await file.read()
            with open(video_path, "wb") as f:
                f.write(contents)
            keyframes_output_dir = os.path.join(tmpdir, "keyframes")
            
            keyframe_paths = extract_keyframes(video_path, keyframes_output_dir, frame_interval=30)
            all_dork_queries = []
            
            for keyframe in keyframe_paths:
                queries = analyze_image_for_dork(keyframe, description)
                all_dork_queries.extend(queries)
            
            unique_dork_queries = list(set(all_dork_queries))
            
            background_tasks.add_task(run_dorking_from_queries, unique_dork_queries)
            
            return unique_dork_queries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

def extract_urls_from_results(html: str) -> list:
    """
    Extracts URLs from DuckDuckGo search results using BeautifulSoup.
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for link in soup.select("a"):
        href = link.get("href", "")
        if href.startswith("https://") and "duckduckgo" not in href:
            urls.append(href)
    return urls

async def search_duckduckgo_dorks(queries: list) -> dict:
    """
    For each Google dork query, search DuckDuckGo and return a dictionary mapping the query to a list of result URLs.
    """
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=HEADERS["User-Agent"])
        page = await context.new_page()
        for query in queries:
            print(f"[Dorking] Searching DuckDuckGo for: {query}")
            search_url = f"https://duckduckgo.com/?q={query}&ia=web"
            try:
                await page.goto(search_url, timeout=60000)
                await page.wait_for_selector("a", timeout=5000)
                html = await page.content()
                urls = extract_urls_from_results(html)
                results[query] = urls
            except Exception as e:
                print(f"[Dorking] Error processing query '{query}': {str(e)}")
                results[query] = []
            # Random delay to avoid bot detection
            await asyncio.sleep(random.uniform(5, 10))
        await browser.close()
    return results

async def submit_url_to_server(url: str):
    """
    Submits a single URL to the /submit endpoint.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("http://localhost:8001/submit", json={"url": url})
            if response.status_code == 200:
                print(f"[Dorking] Submitted URL: {url}")
            else:
                print(f"[Dorking] Failed to submit URL: {url}. Status: {response.status_code}")
        except Exception as e:
            print(f"[Dorking] Error submitting URL: {url}. Error: {str(e)}")

async def run_dorking_from_queries(queries: list):
    """
    Given a list of dork queries, search DuckDuckGo for each query and add found URLs to the batch submission queue.
    This function is meant to run as a background task.
    """
    if not queries:
        print("[Dorking] No queries received. Exiting dorking pipeline.")
        return

    print(f"[Dorking] Running dorking pipeline with {len(queries)} queries.")
    search_results = await search_duckduckgo_dorks(queries)
    
    for query, urls in search_results.items():
        print(f"\n[Dorking] Results for query: {query}")
        if urls:
            for url in urls:
                print(f" - {url}")
                await url_queue.put(url)
        else:
            print("⚠ No results found for this query.")
        print("-" * 50)

async def batch_submit_worker():
    """
    Periodically checks the URL queue and submits URLs in batches.
    Submits every 10 URLs or flushes remaining URLs if they've been waiting for over 30 seconds.
    """
    last_flush_time = time.time()
    while True:
        await asyncio.sleep(5)  # Check every 5 seconds
        if url_queue.qsize() >= 10:
            batch = []
            for _ in range(10):
                batch.append(url_queue.get_nowait())
            last_flush_time = time.time()
            print(f"[Batch Submit] Submitting batch of 10 URLs")
            tasks = [submit_url_to_server(url) for url in batch]
            await asyncio.gather(*tasks)
        elif not url_queue.empty() and (time.time() - last_flush_time) >= 30:
            batch = []
            while not url_queue.empty():
                batch.append(url_queue.get_nowait())
            last_flush_time = time.time()
            print(f"[Batch Submit] Submitting batch of {len(batch)} URLs (flushed after waiting)")
            tasks = [submit_url_to_server(url) for url in batch]
            await asyncio.gather(*tasks)

async def periodic_start_crawling():
    """
    Periodically triggers the start_crawling endpoint every 5 minutes.
    """
    while True:
        try:
            async with httpx.AsyncClient() as client:
                print("[Cron] Hitting start_crawling endpoint")
                response = await client.get("http://localhost:8001/start_crawling")
                if response.status_code == 200:
                    print("[Cron] start_crawling triggered successfully")
                else:
                    print(f"[Cron] Failed to trigger start_crawling. Status: {response.status_code}")
        except Exception as e:
            print(f"[Cron] Error triggering start_crawling: {str(e)}")
        await asyncio.sleep(300)  # Wait for 5 minutes

@app.on_event("startup")
async def startup_event():
    """
    Launch background tasks for batch URL submission and periodic start_crawling.
    """
    asyncio.create_task(batch_submit_worker())
    asyncio.create_task(periodic_start_crawling())

def run_server():
    """
    Runs the FastAPI server using uvicorn.
    """
    uvicorn.run(app, host="0.0.0.0", port=8002)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Integrated Discovery & Dorking Pipeline. "
                    "If a video is provided via '--video', the integrated pipeline will run (after starting the server). "
                    "If no video is provided, the server will run and wait for incoming requests."
    )
    parser.add_argument("--video", help="Path to the video file to be processed (optional).")
    parser.add_argument("--description", default="", help="Optional description/context for video analysis.")
    args = parser.parse_args()

    if args.video:
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        time.sleep(3)

        async def run_client_pipeline():
            async with httpx.AsyncClient() as client:
                with open(args.video, "rb") as f:
                    files = {"file": (os.path.basename(args.video), f, "video/mp4")}
                    data = {"name": os.path.basename(args.video), "description": args.description}
                    resp = await client.post("http://localhost:8002/discover", files=files, data=data)
                    resp.raise_for_status()
                    queries = resp.json()
                    print(f"[Client] Received {len(queries)} queries from /discover endpoint.")
        asyncio.run(run_client_pipeline())
    else:
        run_server()
