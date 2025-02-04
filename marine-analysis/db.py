import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    JSON,
    DateTime,
    Boolean,
    ForeignKey,
    CheckConstraint,
    func,
    text
)
from pgvector.sqlalchemy import Vector

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql+asyncpg://ish:forzajuve!2@4.240.103.202:5432/marine"
else:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True)
Base = declarative_base()
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Table: videos (User-uploaded videos)
class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False)         # Email of the uploader
    filename = Column(String, nullable=False)             # Stored filename or file path (also used as a unique ID)
    title = Column(String)                                # Video title provided by the user
    description = Column(String)                          # Video description provided by the user
    fingerprint = Column(String)                          # Optional: MD5 or other fingerprint of the video file
    hash_vector = Column(Vector(64))                      # Vector representation of the video hash
    audio_spectrum = Column(Vector(128))                  # Vector representation of the audio spectrum
    created_at = Column(DateTime, server_default=func.now())  # Timestamp when the video was uploaded


# Table: crawled_videos (Videos obtained from external sources)

class CrawledVideo(Base):
    __tablename__ = "crawled_videos"

    id = Column(Integer, primary_key=True, index=True)
    video_url = Column(String, nullable=False)          # URL from which the video was crawled
    title = Column(String)                                # Title from the source (if available)
    description = Column(String)                          # Description from the source (if available)
    video_metadata = Column(JSON)                         # Additional metadata as JSON (renamed from "metadata")
    hash_vector = Column(Vector(64))                      # Vector representation of the crawled video's hash
    audio_spectrum = Column(Vector(128))                  # Vector representation of the crawled video's audio spectrum
    crawled_at = Column(DateTime, server_default=func.now())  # Timestamp when the video was crawled

# Table: analyzed_videos
#
# This table stores analysis records for:
#   - An analysis performed on a user-uploaded video (analysis_type = 'uploaded')
#   - An analysis performed on a crawled video (analysis_type = 'crawled')
#   - A comparative analysis between an uploaded and a crawled video (analysis_type = 'comparison')
#
# It includes:
#   - phash_vector: A pgvector column for storing the computed perceptual hash (pHash)
#   - analysis_result: A JSON column for detailed analysis results (e.g. similarity scores)
#   - match_score: A float representing the computed aggregate match score
#   - flagged: A boolean indicating if the video is problematic (e.g. potential piracy)
#
# Two check constraints enforce:
#   1. analysis_type is one of ('uploaded', 'crawled', 'comparison').
#   2. Based on analysis_type, the appropriate foreign key(s) are provided.

class AnalyzedVideo(Base):
    __tablename__ = "analyzed_videos"

    id = Column(Integer, primary_key=True, index=True)
    analysis_type = Column(String, nullable=False)
    uploaded_video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    crawled_video_id = Column(Integer, ForeignKey("crawled_videos.id"), nullable=True)
    phash_vector = Column(Vector(64))               # Vector representation of the computed perceptual hash (pHash)
    analysis_result = Column(JSON)                  # Detailed analysis result (e.g., similarity scores, matching details)
    match_score = Column(Float)                     # Computed match score (if applicable)
    flagged = Column(Boolean, default=False)        # Flag indicating issues (e.g., potential piracy)
    analyzed_at = Column(DateTime, server_default=func.now())  # Timestamp when the analysis was performed

    __table_args__ = (
        CheckConstraint(
            "analysis_type IN ('uploaded', 'crawled', 'comparison')", name="chk_analysis_type"
        ),
        CheckConstraint(
            "((analysis_type = 'uploaded' AND uploaded_video_id IS NOT NULL AND crawled_video_id IS NULL) OR " +
            "(analysis_type = 'crawled' AND crawled_video_id IS NOT NULL AND uploaded_video_id IS NULL) OR " +
            "(analysis_type = 'comparison' AND uploaded_video_id IS NOT NULL AND crawled_video_id IS NOT NULL))",
            name="chk_analysis_type_relation"
        ),
    )

# Initialize the database by creating all tables.

async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
