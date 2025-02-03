import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter

router = APIRouter()

def scrape_page(url: str):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find("title").text if soup.find("title") else "No Title"
        text_content = " ".join([p.text for p in soup.find_all("p")])

        return {"url": url, "title": title, "content": text_content[:500]}  # Limit text
    except Exception as e:
        return {"url": url, "error": str(e)}

@router.get("/scrape")
async def scrape_endpoint(url: str):
    return scrape_page(url)
