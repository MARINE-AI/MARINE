import asyncio
import random
import argparse
import os
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

def extract_urls_from_results(html: str) -> list:
    """Extracts URLs from DuckDuckGo search results."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    
    for link in soup.select("a"):
        href = link.get("href", "")
        if href.startswith("https://") and "duckduckgo" not in href:
            urls.append(href)
    return urls

async def search_duckduckgo_dorks(queries: list) -> dict:
    """
    Automates DuckDuckGo searches for given queries and extracts result URLs.

    :param queries: A list of dork query strings.
    :return: A dictionary mapping each query to a list of result URLs.
    """
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=HEADERS["User-Agent"])
        page = await context.new_page()

        for query in queries:
            print(f"Searching DuckDuckGo for: {query}")
            search_url = f"https://duckduckgo.com/?q={query}&ia=web"
            await page.goto(search_url, timeout=60000)
            await page.wait_for_selector("a", timeout=5000)
            html = await page.content()
            urls = extract_urls_from_results(html)
            results[query] = urls

            await asyncio.sleep(random.uniform(5, 10))  # Delay to avoid triggering bot detection
        
        await browser.close()
    return results

async def submit_url(url: str):
    """Submits a URL to the server's /submit endpoint."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("http://localhost:8002/submit", json={"url": url})
            if response.status_code == 200:
                print(f"Submitted URL: {url}")
            else:
                print(f"Failed to submit URL: {url}. Status: {response.status_code}")
        except Exception as e:
            print(f"Error submitting URL: {url}. Error: {str(e)}")

async def get_dork_queries(video_path: str, description: str) -> list:
    """
    Sends the video file (and description) to the /discover endpoint and retrieves
    a JSON array of unique Google dork queries.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    async with httpx.AsyncClient() as client:
        with open(video_path, "rb") as f:
            files = {"file": (os.path.basename(video_path), f, "video/mp4")}
            data = {"name": os.path.basename(video_path), "description": description}
            response = await client.post("http://localhost:8002/discover", files=files, data=data)
            response.raise_for_status()
            queries = response.json()
            print(f"Received {len(queries)} queries from /discover endpoint.")
            return queries

async def main():
    parser = argparse.ArgumentParser(description="Video-based dork query generator and URL submitter.")
    parser.add_argument("--video", required=True, help="Path to the video file to be processed.")
    parser.add_argument("--description", default="", help="Optional description/context for video analysis.")
    args = parser.parse_args()

    # Step 1: Get dork queries from the /discover endpoint using the provided video.
    queries = await get_dork_queries(args.video, args.description)
    if not queries:
        print("No queries received. Exiting.")
        return

    # Step 2: Use the queries to search DuckDuckGo and collect result URLs.
    search_results = await search_duckduckgo_dorks(queries)

    # Step 3: For every result URL, submit it to the /submit endpoint.
    for query, urls in search_results.items():
        print(f"\nResults for query: {query}")
        if urls:
            for url in urls:
                print(f" - {url}")
                await submit_url(url)
        else:
            print("⚠ No results found for this query.")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
