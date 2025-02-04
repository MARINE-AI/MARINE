from fastapi import FastAPI
from dorking import router as dorking_router
from scraper import router as scraper_router

app = FastAPI()

# Include routers correctly
app.include_router(dorking_router, prefix="/dork", tags=["Google Dorking"])
app.include_router(scraper_router, prefix="/scrape", tags=["Web Scraping"])

# Health check
@app.get("/")
def root():
    return {"message": "Dorking & Scraping Microservices are running!"}
    