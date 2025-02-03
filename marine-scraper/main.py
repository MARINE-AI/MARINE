from fastapi import FastAPI
from dorking import router as dorking_router
from scraper import router as scraper_router

app = FastAPI(title="Piracy Detection Microservice")

app.include_router(dorking_router, prefix="/api/dorking")
app.include_router(scraper_router, prefix="/api/scraper")

@app.get("/")
def home():
    return {"message": "Piracy Detection Microservice is running!"}
