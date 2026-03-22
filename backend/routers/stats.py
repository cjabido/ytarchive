"""
Stats endpoint — aggregate metrics for the dashboard.
"""

from fastapi import APIRouter, Depends
import aiosqlite

from database import get_db
from models import StatsOut, TopChannel

router = APIRouter()


@router.get("/stats", response_model=StatsOut)
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    async def scalar(sql: str, params: list = []) -> int:
        async with db.execute(sql, params) as c:
            row = await c.fetchone()
            return row[0] if row else 0

    total_videos = await scalar("SELECT COUNT(*) FROM videos")
    unique_videos = await scalar("SELECT COUNT(DISTINCT video_id) FROM videos")
    total_channels = await scalar("SELECT COUNT(*) FROM channels")
    total_tags = await scalar("SELECT COUNT(*) FROM tags")
    watchlist_count = await scalar("SELECT COUNT(*) FROM watchlist")
    transcript_count = await scalar("SELECT COUNT(*) FROM transcripts")
    rewatched_count = await scalar("""
        SELECT COUNT(*) FROM (
            SELECT video_id FROM videos GROUP BY video_id HAVING COUNT(*) > 1
        )
    """)

    # Top 10 channels by watch count
    async with db.execute("""
        SELECT c.channel_name, COUNT(*) as watch_count
        FROM videos v
        JOIN channels c ON v.channel_id = c.channel_id
        GROUP BY c.channel_id
        ORDER BY watch_count DESC
        LIMIT 10
    """) as cursor:
        top_rows = await cursor.fetchall()

    top_channels = [
        TopChannel(channel_name=r["channel_name"], watch_count=r["watch_count"])
        for r in top_rows
    ]

    # Watchlist by status
    async with db.execute(
        "SELECT status, COUNT(*) as cnt FROM watchlist GROUP BY status"
    ) as cursor:
        status_rows = await cursor.fetchall()

    watchlist_by_status = {r["status"]: r["cnt"] for r in status_rows}

    # Views by hour of day (0-23)
    async with db.execute("""
        SELECT strftime('%H', watched_at) as hour, COUNT(*) as cnt
        FROM videos
        GROUP BY hour
        ORDER BY hour
    """) as cursor:
        hour_rows = await cursor.fetchall()

    watches_by_hour = {r["hour"]: r["cnt"] for r in hour_rows}

    return StatsOut(
        total_videos=total_videos,
        unique_videos=unique_videos,
        total_channels=total_channels,
        total_tags=total_tags,
        watchlist_count=watchlist_count,
        transcript_count=transcript_count,
        rewatched_count=rewatched_count,
        top_channels=top_channels,
        watchlist_by_status=watchlist_by_status,
        watches_by_hour=watches_by_hour,
    )
