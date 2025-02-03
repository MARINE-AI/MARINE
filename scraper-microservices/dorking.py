from playwright.async_api import async_playwright
from fastapi import APIRouter
import asyncio

router = APIRouter()

async def google_dork(query: str, num_results: int = 5):
    urls = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"https://www.google.com/search?q={query}")

        results = await page.query_selector_all("div.tF2Cxc a")
        for result in results[:num_results]:
            link = await result.get_attribute("href")
            if link:
                urls.append(link)

        await browser.close()
    
    return urls

@router.get("/dork")
async def dorking_endpoint(query: str, num_results: int = 5):
    urls = await google_dork(query, num_results)
    return {"query": query, "results": urls}
