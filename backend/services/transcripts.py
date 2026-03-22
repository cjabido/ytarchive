"""
Transcript fetch service.
Uses youtube-transcript-api v1.x (instance-based API).
"""

import asyncio
import logging
import os
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        CouldNotRetrieveTranscript,
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False
    logger.warning("youtube-transcript-api not installed")


DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent.parent / "youtube_history.db"))
PREFERRED_LANGUAGES = ["en", "en-US", "en-GB"]


def _fetch_transcript_sync(video_id: str) -> tuple[str, str]:
    """
    Fetch transcript synchronously (library is sync-only).
    Returns (text, language_code).
    Uses the v1.x instance-based API: YouTubeTranscriptApi().fetch(...)
    """
    if not TRANSCRIPT_API_AVAILABLE:
        raise RuntimeError("youtube-transcript-api is not installed")

    api = YouTubeTranscriptApi()

    # Try preferred languages first (fetch raises if not available)
    for lang in PREFERRED_LANGUAGES:
        try:
            result = api.fetch(video_id, languages=[lang])
            text = " ".join(s.text for s in result)
            return text, result.language_code
        except (NoTranscriptFound, CouldNotRetrieveTranscript):
            continue

    # Fall back: list available transcripts and take the first
    transcript_list = api.list(video_id)
    for t in transcript_list:
        result = api.fetch(video_id, languages=[t.language_code])
        text = " ".join(s.text for s in result)
        return text, result.language_code

    raise NoTranscriptFound(video_id, PREFERRED_LANGUAGES)


async def fetch_and_store_transcript(video_id: str) -> bool:
    """
    Background task: fetch a transcript and store it in the DB.
    Returns True on success, False on failure.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            "SELECT video_id FROM transcripts WHERE video_id = ?", [video_id]
        ) as cursor:
            if await cursor.fetchone():
                return True  # already stored

        try:
            loop = asyncio.get_event_loop()
            text, language = await loop.run_in_executor(
                None, _fetch_transcript_sync, video_id
            )
            await db.execute(
                "INSERT OR REPLACE INTO transcripts (video_id, transcript, language) VALUES (?, ?, ?)",
                [video_id, text, language],
            )
            await db.commit()
            logger.info("Transcript stored for %s (%s)", video_id, language)
            return True
        except Exception as e:
            logger.error("Transcript fetch failed for %s: %s", video_id, e)
            return False
