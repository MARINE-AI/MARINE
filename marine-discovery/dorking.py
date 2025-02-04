import asyncio
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

def extract_urls_from_results(html):
    """Extracts URLs from DuckDuckGo search results."""
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    
    for link in soup.select("a"):
        href = link.get("href", "")
        if href.startswith("https://") and "duckduckgo" not in href:
            urls.append(href)  # Store only valid result links
    
    return urls

async def search_duckduckgo_dorks(queries):
    """Automates DuckDuckGo searches for given queries and extracts result URLs."""
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)  # Headful mode for debugging
        context = await browser.new_context(user_agent=HEADERS["User-Agent"])
        page = await context.new_page()

        for query in queries:
            print(f"Searching: {query}")
            
            search_url = f"https://duckduckgo.com/?q={query}&ia=web"
            await page.goto(search_url, timeout=60000)
            await page.wait_for_selector("a", timeout=5000)  # Ensure results load
            
            html = await page.content()
            urls = extract_urls_from_results(html)
            results[query] = urls

            await asyncio.sleep(random.uniform(5, 10))  # Random delay to avoid detection
        
        await browser.close()
    
    return results

if _name_ == "_main_":
    queries = [
        "intitle:\"F1\" intext:\"Ferrari\" intext:\"Charles Leclerc\" site:formula1.com",
        "intitle:\"Bahrain Grand Prix\" intext:\"Ferrari SF-23\" inurl:video",
        "site:youtube.com \"Ferrari F1 2023\" \"Charles Leclerc\" \"Bahrain\"",
        "\"Ferrari SF-23\" \"onboard\" \"Bahrain International Circuit\"",
        "intext:\"Scuderia Ferrari\" intext:\"2023 season\" intext:\"race highlights\""
    ]

    results = asyncio.run(search_duckduckgo_dorks(queries))

    for query, urls in results.items():
        print(f"\nResults for: {query}")
        if urls:
            for url in urls:
                print(url)
        else:
            print("⚠ No results found. DuckDuckGo might be blocking requests.")
        print("-" * 50)