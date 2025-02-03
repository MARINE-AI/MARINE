import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Boolean, func

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ish:forzajuve!2@4.240.103.202:5432/marine")

engine = create_async_engine(DATABASE_URL, echo=True)
Base = declarative_base()
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class VideoFingerprint(Base):
    __tablename__ = "video_fingerprints"
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
