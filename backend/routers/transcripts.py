"""
Transcript endpoints: fetch, retrieve, Obsidian export.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
import aiosqlite

from database import get_db
from models import TranscriptOut

router = APIRouter()


@router.get("/transcripts/{video_id}", response_model=TranscriptOut)
async def get_transcript(video_id: str, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute(
        "SELECT * FROM transcripts WHERE video_id = ?", [video_id]
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No transcript stored for this video")
    return TranscriptOut(
        video_id=row["video_id"],
        transcript=row["transcript"],
        language=row["language"],
        fetched_at=row["fetched_at"],
    )


@router.post("/transcripts/{video_id}/fetch")
async def trigger_transcript_fetch(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: aiosqlite.Connection = Depends(get_db),
):
    # Already have it — return 200 immediately
    async with db.execute(
        "SELECT video_id FROM transcripts WHERE video_id = ?", [video_id]
    ) as cursor:
        if await cursor.fetchone():
            return {"status": "exists", "video_id": video_id}

    # Verify video exists in DB
    async with db.execute(
        "SELECT video_id FROM videos WHERE video_id = ? LIMIT 1", [video_id]
    ) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Video not found")

    from services.transcripts import fetch_and_store_transcript
    background_tasks.add_task(fetch_and_store_transcript, video_id)
    return {"status": "fetching", "video_id": video_id}


@router.get("/transcripts/{video_id}/obsidian", response_class=PlainTextResponse)
async def export_transcript_obsidian(
    video_id: str, db: aiosqlite.Connection = Depends(get_db)
):
    async with db.execute("""
        SELECT
            v.video_title, v.video_url,
            c.channel_name,
            MAX(v.watched_at) as last_watched,
            t.transcript, t.language,
            GROUP_CONCAT(DISTINCT tg.name) as tags
        FROM transcripts t
        JOIN videos v ON t.video_id = v.video_id
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        LEFT JOIN video_tags vt ON v.video_id = vt.video_id
        LEFT JOIN tags tg ON vt.tag_id = tg.id
        WHERE t.video_id = ?
        GROUP BY t.video_id
    """, [video_id]) as cursor:
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No transcript found")

    tags_yaml = ", ".join(["youtube"] + (row["tags"].split(",") if row["tags"] else []))
    watched_date = (row["last_watched"] or "")[:10]

    markdown = f"""---
title: "{row['video_title']}"
channel: "{row['channel_name'] or 'Unknown'}"
url: {row['video_url']}
watched: {watched_date}
tags: [{tags_yaml}]
---

# {row['video_title']}

**Channel:** {row['channel_name'] or 'Unknown'}
**URL:** {row['video_url']}

## Transcript

{row['transcript']}
"""
    return PlainTextResponse(content=markdown, media_type="text/markdown")
