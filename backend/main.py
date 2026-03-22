"""
YTArchive FastAPI backend entry point.

Run with:
    cd backend
    uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database import run_migrations
from routers import videos, tags, watchlist, transcripts, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    yield


app = FastAPI(
    title="YTArchive API",
    description="Personal YouTube watch history management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow React dev server and Safari extension
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(videos.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(transcripts.router, prefix="/api")
app.include_router(stats.router, prefix="/api")

# Serve built React frontend in production (backend/static/)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
