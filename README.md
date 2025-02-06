<p align="center">
  <h3 align="center">MARINE</h3>
  <p align="center">
    A distributed microservices system for detecting pirated video content. Marine integrates several microservices for video analysis, crawling, and discovery.
    <br /><br />
  </p>
</p>

---

<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about">About</a></li>
    <li><a href="#features">Features</a></li>
    <li><a href="#built-with">Built With</a></li>
    <li><a href="#project-structure">Project Structure</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#configuration">Configuration</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#database-schema">Database Schema</a></li>
    <li><a href="#microservices-overview">Microservices Overview</a></li>
    <li><a href="#contributing">Contributing</a></li>
  </ol>
</details>

---

## About

MARINE is a distributed system designed to help content owners detect pirated video content across the web. It consists of several specialized microservices that work together to:

- Analyze videos using advanced fingerprinting techniques.
- Crawl websites to download and segment video content.
- Discover potential piracy sites via metadata search and Google dorking.
- Manage user uploads through a SaaS dashboard with a Golang backend (Next.js/TailwindCSS frontend).

---

## Features

- **Video Analysis:**  
  Extract keyframes, compute perceptual hashes (pHashes), and (optionally) generate audio fingerprints from video files.

- **Dual Pipeline Storage:**  
  - **Uploaded Videos:** Videos uploaded by content owners are processed and stored in the `uploaded_videos` table.
  - **Crawled Videos:** Videos discovered via crawling are segmented into chunks, reassembled, and analyzed; the results are stored in the `crawled_videos` table.

- **Active Matching:**  
  The system actively compares uploaded videos against crawled videos to flag potential piracy.

- **Distributed Architecture:**  
  Combines multiple microservices:
  - **Analysis Microservice:** Built with Python and FastAPI.
  - **Golang Backend:** Processes user uploads via Kafka (SaaS dashboard built with Next.js/TailwindCSS).
  - **Crawler Microservice:** Crawls URLs and downloads video content using ffmpeg, yt-dlp, and other tools.
  - **Discovery Microservice:** Uses Google dorking and metadata search to discover sites that might host copyrighted content.

---

## Built With

- **Python, FastAPI** – For building asynchronous web services.
- **Uvicorn** – ASGI server for running FastAPI.
- **SQLAlchemy (with asyncpg)** – For asynchronous database operations.
- **aiokafka** – For Kafka integration.
- **Redis** – For caching fingerprints (if used).
- **Loguru** – For logging.
- **ffmpeg, yt-dlp** – For video downloading, segmentation, and reassembly.
- **Golang, Next.js, TailwindCSS** – For the SaaS dashboard backend and frontend.
- **Google Dorking & Metadata Search** – Used in the Discovery microservice.

---

## Project Structure

The project is organized into four main components:

```
marine/
├── marine-analysis
│   ├── fingerprint/        # Contains modules for video and audio fingerprinting
│   ├── storage/            # Redis utilities for caching fingerprints
│   ├── config.py           # FastAPI configuration settings
│   ├── db.py               # Database schema & initialization (models for analysis)
│   ├── main.py             # AI microservice endpoints (video analysis, chunk processing)
│   └── requirements.txt    # Python dependencies for the analysis service
├── marine-backend
│   ├── config/             # Go configuration files
│   ├── controllers/        # API controllers (e.g., video, report)
│   ├── eventhandlers/      # Kafka event handler(s)
│   ├── models/             # Data models in Go
│   ├── services/           # Business logic and client services (e.g., AI service client)
│   ├── go.mod, go.sum      # Go module files
│   └── main.go             # Entry point for the Golang backend
├── marine-crawler
│   ├── app/
│   │   ├── storage/        # Redis utilities (Python)
│   │   ├── config.py       # Crawler configuration
│   │   ├── crawler.py      # Logic for crawling URLs and extracting video links
│   │   ├── downloader.py   # Downloads videos using yt-dlp and ffmpeg
│   │   ├── kafka_client.py # Kafka integration for sending download tasks
│   │   └── main.py         # Entry point for the crawler microservice
│   ├── requirements.txt    # Python dependencies for the crawler
│   └── run.py              # Script to start the crawler service
├── marine-dashboard
│   ├── app/                # Next.js app with API routes, components, and layout files
│   ├── lib/                # Utility functions (e.g., auth)
│   ├── config files
│   ├── package.json        # Node.js dependencies for the dashboard
│   └── README.md           # Documentation for the dashboard
├── marine-discovery
│   ├── config.py           # Configuration for the discovery service
│   ├── dorking.py          # Module for performing Google dorking
│   ├── main.py             # Entry point for the discovery service
│   ├── requirements.txt    # Python dependencies for discovery
│   └── scraper.py          # Scraping logic for discovering potential piracy sites
└── .gitignore              # Global git ignore file

```

---

## Installation

### Marine Analysis (AI Microservice)

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/Marine.git
   cd Marine/marine-analysis
   ```

2. **Create and Activate a Virtual Environment:**

   - On Linux/macOS:
     ```bash
     python -m venv env
     source env/bin/activate
     ```
   - On Windows:
     ```bash
     python -m venv env
     env\Scripts\activate
     ```

3. **Install Python Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

### Marine Backend (Golang)

1. Navigate to the backend directory:

   ```bash
   cd ../marine-backend
   ```

2. Build the Golang application:

   ```bash
   go build -o marine-backend
   ```

### Marine Crawler

1. Navigate to the crawler directory:

   ```bash
   cd ../marine-crawler
   ```

2. Create and activate a virtual environment, then install dependencies:

   ```bash
   python -m venv env
   source env/bin/activate
   pip install -r requirements.txt
   ```

### Marine Dashboard

1. Navigate to the dashboard directory:

   ```bash
   cd ../marine-dashboard
   ```

2. Install Node dependencies:

   ```bash
   npm install
   ```

### Marine Discovery

1. Navigate to the discovery directory:

   ```bash
   cd ../marine-discovery
   ```

2. Create and activate a virtual environment (if using Python), then install dependencies:

   ```bash
   python -m venv env
   source env/bin/activate
   pip install -r requirements.txt
   ```

---

## Configuration

Each microservice is configured via environment variables. Create a `.env` file in the project root with contents similar to the following:

```
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=your.kafka.server:9092
KAFKA_CRAWL_TOPIC=crawl-tasks
KAFKA_VIDEO_DOWNLOAD_TOPIC=video-download-tasks
KAFKA_VIDEO_CHUNKS_TOPIC=video-chunks

# Redis Configuration
REDIS_HOST=your.redis.server
REDIS_PORT=6379
REDIS_DB=0

# Video Analysis Configuration
FRAMES_DIR=frames
SIMILARITY_THRESHOLD=0.8
REFERENCE_REDIS_KEY=ref_phashes

# AI Microservice URL (if used by other services)
AI_MICROSERVICE_URL=http://localhost:8000
```

Adjust the values as needed for your environment.

---

## Usage

### Analysis Microservice (Marine Analysis)

#### Content Owner Pipeline
- **Endpoint:** `/match-video`  
- **Method:** POST  
- **Description:**  
  Content owners upload a full video. The service extracts keyframes, computes pHashes (and optionally audio fingerprints), and upserts the analysis result in the `uploaded_videos` table. The video is actively matched against crawled videos in the database.

#### Crawled Video Pipeline
- **Endpoint:** `/upload-video-chunk`  
- **Method:** POST  
- **Description:**  
  The crawler uploads video chunks to this endpoint. Once all chunks are received, a background task automatically reassembles the video and triggers the analysis pipeline.

- **Endpoint:** `/analyze`  
- **Method:** POST  
- **Description:**  
  Manually triggers the reassembly and analysis of a crawled video. The analysis result is stored in the `crawled_videos` table.

### Golang Backend
- **Description:**  
  The Golang backend, built with Kafka, handles user uploads from a SaaS dashboard (Next.js/TailwindCSS) and forwards upload events to the Analysis Microservice.

### Marine Crawler
- **Description:**  
  The crawler microservice crawls websites for video content using tools like ffmpeg and yt-dlp, downloads videos, segments them into chunks, and sends them for analysis.

### Marine Discovery
- **Description:**  
  Uses Google dorking and metadata search techniques to discover websites that may host copyrighted content.

---

## Database Schema

The database schema is defined in **marine-analysis/db.py**. Two tables are used:

- **UploadedVideo:**  
  Stores analysis results from videos uploaded by content owners.
  
- **CrawledVideo:**  
  Stores analysis results from videos obtained via crawling.

Example schema:

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Boolean, func

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/dbname")

engine = create_async_engine(DATABASE_URL, echo=True)
Base = declarative_base()
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class UploadedVideo(Base):
    __tablename__ = "uploaded_videos"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, unique=True, index=True)
    video_url = Column(String)
    match_score = Column(Float, nullable=True)
    uploaded_phashes = Column(JSON)
    audio_spectrum = Column(JSON, nullable=True)
    flagged = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class CrawledVideo(Base):
    __tablename__ = "crawled_videos"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, unique=True, index=True)
    video_url = Column(String)
    match_score = Column(Float, nullable=True)
    uploaded_phashes = Column(JSON)
    audio_spectrum = Column(JSON, nullable=True)
    flagged = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

## Running the Services

### Marine Analysis (AI Microservice)

From the `marine-analysis` directory, run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Alternatively, using the `run.py` at the root:

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
```

Then execute:

```bash
python run.py
```

### Marine Backend

From the `marine-backend` directory, build and run:

```bash
./marine-backend
```

### Marine Crawler

From the `marine-crawler` directory, run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Marine Discovery

Follow the instructions in the `marine-discovery` directory to build and run that service.

---

## Logging

Logging is managed using Loguru. Logs are output to the console and provide detailed information about application startup, processing, and errors.

---

## Contributing

Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a feature branch:  
   ```bash
   git checkout -b feature/my-feature
   ```
3. Commit your changes.
4. Push to your fork and open a pull request.

For major changes, please open an issue first to discuss your ideas.

---
