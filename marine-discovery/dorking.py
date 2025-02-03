from playwright.async_api import async_playwright
from fastapi import APIRouter, HTTPException
import asyncio

router = APIRouter()

async def google_dork(query: str, num_results: int = 5):
    urls = []
    try:
        async with async_playwright() as p:
            print("Launching browser...")  # DEBUG
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            search_url = f"https://www.google.com/search?q={query}"
            print(f"Navigating to: {search_url}")  # DEBUG
            await page.goto(search_url)

            results = await page.query_selector_all("div.tF2Cxc a")
            print(f"Found {len(results)} results")  # DEBUG

            for result in results[:num_results]:
                link = await result.get_attribute("href")
                if link:
                    urls.append(link)

            await browser.close()
    except Exception as e:
        print(f"ERROR: {str(e)}")  # DEBUG
        raise HTTPException(status_code=500, detail=str(e))
    
    return urls

@router.get("/dork")
async def dorking_endpoint(query: str, num_results: int = 5):
    urls = await google_dork(query, num_results)
    return {"query": query, "results": urls}
