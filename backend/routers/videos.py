"""
Video endpoints: browse/search, detail, add (Safari extension), tags, notes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
import aiosqlite

from database import get_db
from models import (
    VideoListResponse, VideoListItem, VideoDetail, VideoCreate,
    SetTagsRequest, TagOut, WatchEntry, WatchlistItem, TranscriptOut,
    NotesOut, NotesUpsert,
)

router = APIRouter()


# ──────────────────────────── GET /videos ────────────────────────────

@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    q: Optional[str] = None,
    channel: Optional[str] = None,
    channel_exact: Optional[str] = None,
    tag: Optional[str] = None,
    watchlist_status: Optional[str] = None,
    has_transcript: Optional[bool] = None,
    rewatched: Optional[bool] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    sort: str = Query("last_watched", pattern="^(last_watched|watch_count|title)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: aiosqlite.Connection = Depends(get_db),
):
    conditions = []
    params: list = []

    if q:
        conditions.append("v.video_title LIKE ?")
        params.append(f"%{q}%")
    if channel:
        conditions.append("c.channel_name LIKE ?")
        params.append(f"%{channel}%")
    if channel_exact:
        conditions.append("c.channel_name = ?")
        params.append(channel_exact)
    if tag:
        conditions.append("""
            v.video_id IN (
                SELECT vt.video_id FROM video_tags vt
                JOIN tags t ON vt.tag_id = t.id
                WHERE t.name = ?
            )
        """)
        params.append(tag)
    if watchlist_status:
        conditions.append("w.status = ?")
        params.append(watchlist_status)
    if has_transcript is True:
        conditions.append("tr.video_id IS NOT NULL")
    elif has_transcript is False:
        conditions.append("tr.video_id IS NULL")
    if rewatched is True:
        conditions.append("COUNT(v.id) > 1")
    if from_date:
        conditions.append("MAX(v.watched_at) >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("MAX(v.watched_at) <= ?")
        params.append(to_date)

    where_clause = ("HAVING " + " AND ".join(conditions)) if conditions else ""
    # Move non-aggregate conditions to WHERE for query optimizer
    pre_having = []
    having_only = []
    for cond, param in zip(conditions, params):
        if any(agg in cond for agg in ("COUNT(", "MAX(")):
            having_only.append((cond, param))
        else:
            pre_having.append((cond, param))

    where_sql = ("WHERE " + " AND ".join(c for c, _ in pre_having)) if pre_having else ""
    having_sql = ("HAVING " + " AND ".join(c for c, _ in having_only)) if having_only else ""
    where_params = [p for _, p in pre_having]
    having_params = [p for _, p in having_only]

    sort_map = {
        "last_watched": "last_watched DESC",
        "watch_count": "watch_count DESC",
        "title": "v.video_title ASC",
    }
    order_sql = sort_map.get(sort, "last_watched DESC")

    base_query = f"""
        SELECT
            v.video_id,
            v.video_title,
            v.video_url,
            MAX(c.channel_name) as channel_name,
            MAX(c.channel_url) as channel_url,
            MAX(v.watched_at) as last_watched,
            COUNT(DISTINCT v.id) as watch_count,
            w.status as watchlist_status,
            GROUP_CONCAT(DISTINCT t.name) as tags,
            CASE WHEN tr.video_id IS NOT NULL THEN 1 ELSE 0 END as has_transcript
        FROM videos v
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        LEFT JOIN watchlist w ON v.video_id = w.video_id
        LEFT JOIN video_tags vt ON v.video_id = vt.video_id
        LEFT JOIN tags t ON vt.tag_id = t.id
        LEFT JOIN transcripts tr ON v.video_id = tr.video_id
        {where_sql}
        GROUP BY v.video_id
        {having_sql}
    """

    # Count total matching
    count_query = f"SELECT COUNT(*) FROM ({base_query})"
    async with db.execute(count_query, where_params + having_params) as cursor:
        row = await cursor.fetchone()
        total = row[0] if row else 0

    # Paginated results
    offset = (page - 1) * per_page
    results_query = base_query + f" ORDER BY {order_sql} LIMIT ? OFFSET ?"
    async with db.execute(results_query, where_params + having_params + [per_page, offset]) as cursor:
        rows = await cursor.fetchall()

    videos = []
    for row in rows:
        videos.append(VideoListItem(
            video_id=row["video_id"],
            video_title=row["video_title"],
            video_url=row["video_url"],
            channel_name=row["channel_name"],
            channel_url=row["channel_url"],
            last_watched=row["last_watched"],
            watch_count=row["watch_count"],
            watchlist_status=row["watchlist_status"],
            tags=row["tags"].split(",") if row["tags"] else [],
            has_transcript=bool(row["has_transcript"]),
        ))

    return VideoListResponse(total=total, page=page, per_page=per_page, videos=videos)


# ──────────────────────────── GET /videos/{video_id} ────────────────────────────

@router.get("/videos/{video_id}", response_model=VideoDetail)
async def get_video(video_id: str, db: aiosqlite.Connection = Depends(get_db)):
    # Base video info
    async with db.execute("""
        SELECT v.video_id, v.video_title, v.video_url, c.channel_name, c.channel_url
        FROM videos v
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        WHERE v.video_id = ?
        ORDER BY v.channel_id IS NOT NULL DESC
        LIMIT 1
    """, [video_id]) as cursor:
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Video not found")

    # All watch timestamps
    async with db.execute(
        "SELECT watched_at FROM videos WHERE video_id = ? ORDER BY watched_at DESC",
        [video_id]
    ) as cursor:
        watch_rows = await cursor.fetchall()

    # Tags
    async with db.execute("""
        SELECT t.id, t.name, t.color FROM tags t
        JOIN video_tags vt ON t.id = vt.tag_id
        WHERE vt.video_id = ?
    """, [video_id]) as cursor:
        tag_rows = await cursor.fetchall()

    # Watchlist
    async with db.execute(
        "SELECT * FROM watchlist WHERE video_id = ?", [video_id]
    ) as cursor:
        wl_row = await cursor.fetchone()

    # Notes
    async with db.execute(
        "SELECT content, updated_at FROM video_notes WHERE video_id = ?", [video_id]
    ) as cursor:
        notes_row = await cursor.fetchone()

    # Transcript
    async with db.execute(
        "SELECT transcript, language, fetched_at FROM transcripts WHERE video_id = ?", [video_id]
    ) as cursor:
        tr_row = await cursor.fetchone()

    return VideoDetail(
        video_id=row["video_id"],
        video_title=row["video_title"],
        video_url=row["video_url"],
        channel_name=row["channel_name"],
        channel_url=row["channel_url"],
        watch_history=[WatchEntry(watched_at=r["watched_at"]) for r in watch_rows],
        watch_count=len(watch_rows),
        tags=[TagOut(id=r["id"], name=r["name"], color=r["color"]) for r in tag_rows],
        watchlist=WatchlistItem(**dict(wl_row)) if wl_row else None,
        notes=notes_row["content"] if notes_row else None,
        transcript=TranscriptOut(
            video_id=video_id,
            transcript=tr_row["transcript"],
            language=tr_row["language"],
            fetched_at=tr_row["fetched_at"],
        ) if tr_row else None,
    )


# ──────────────────────────── POST /videos ────────────────────────────

@router.post("/videos", status_code=201)
async def add_video(
    body: VideoCreate,
    background_tasks: BackgroundTasks,
    db: aiosqlite.Connection = Depends(get_db),
):
    from services.transcripts import fetch_and_store_transcript

    # Upsert channel (channel_url doubles as channel_id; skip if not provided)
    if body.channel_url:
        await db.execute("""
            INSERT OR IGNORE INTO channels (channel_id, channel_name, channel_url, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
        """, [body.channel_url, body.channel_name, body.channel_url, body.watched_at, body.watched_at])
        await db.execute("""
            UPDATE channels SET last_seen = ?, channel_name = ?
            WHERE channel_id = ? AND last_seen < ?
        """, [body.watched_at, body.channel_name, body.channel_url, body.watched_at])

    # Check for existing entry
    async with db.execute(
        "SELECT id FROM videos WHERE video_id = ? AND watched_at = ?",
        [body.video_id, body.watched_at]
    ) as cursor:
        existing = await cursor.fetchone()

    if not existing:
        await db.execute("""
            INSERT INTO videos (video_id, video_url, video_title, channel_id, watched_at)
            VALUES (?, ?, ?, ?, ?)
        """, [body.video_id, body.video_url, body.video_title, body.channel_url or None, body.watched_at])

    # Apply tags by name
    for tag_name in body.tags:
        async with db.execute("SELECT id FROM tags WHERE name = ?", [tag_name]) as cursor:
            tag_row = await cursor.fetchone()
        if tag_row:
            await db.execute(
                "INSERT OR IGNORE INTO video_tags (video_id, tag_id) VALUES (?, ?)",
                [body.video_id, tag_row["id"]]
            )

    # Watchlist entry
    if body.watchlist_status:
        await db.execute("""
            INSERT INTO watchlist (video_id, status) VALUES (?, ?)
            ON CONFLICT(video_id) DO UPDATE SET status = excluded.status, updated_at = CURRENT_TIMESTAMP
        """, [body.video_id, body.watchlist_status])

    # Notes
    if body.notes:
        await db.execute("""
            INSERT INTO video_notes (video_id, content) VALUES (?, ?)
            ON CONFLICT(video_id) DO UPDATE SET content = excluded.content, updated_at = CURRENT_TIMESTAMP
        """, [body.video_id, body.notes])

    await db.commit()

    if body.fetch_transcript:
        background_tasks.add_task(fetch_and_store_transcript, body.video_id)

    return await get_video(body.video_id, db)


# ──────────────────────────── Tag endpoints on videos ────────────────────────────

@router.put("/videos/{video_id}/tags")
async def set_video_tags(
    video_id: str,
    body: SetTagsRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    await db.execute("DELETE FROM video_tags WHERE video_id = ?", [video_id])
    for tag_id in body.tag_ids:
        await db.execute(
            "INSERT OR IGNORE INTO video_tags (video_id, tag_id) VALUES (?, ?)",
            [video_id, tag_id]
        )
    await db.commit()

    async with db.execute("""
        SELECT t.id, t.name, t.color FROM tags t
        JOIN video_tags vt ON t.id = vt.tag_id
        WHERE vt.video_id = ?
    """, [video_id]) as cursor:
        rows = await cursor.fetchall()

    return {"video_id": video_id, "tags": [dict(r) for r in rows]}


@router.post("/videos/{video_id}/tags/{tag_id}", status_code=201)
async def add_video_tag(
    video_id: str, tag_id: int, db: aiosqlite.Connection = Depends(get_db)
):
    async with db.execute("SELECT id FROM tags WHERE id = ?", [tag_id]) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Tag not found")
    await db.execute(
        "INSERT OR IGNORE INTO video_tags (video_id, tag_id) VALUES (?, ?)",
        [video_id, tag_id]
    )
    await db.commit()
    return {"video_id": video_id, "tag_id": tag_id}


@router.delete("/videos/{video_id}/tags/{tag_id}", status_code=204)
async def remove_video_tag(
    video_id: str, tag_id: int, db: aiosqlite.Connection = Depends(get_db)
):
    await db.execute(
        "DELETE FROM video_tags WHERE video_id = ? AND tag_id = ?",
        [video_id, tag_id]
    )
    await db.commit()


# ──────────────────────────── Notes ────────────────────────────

@router.get("/videos/{video_id}/notes", response_model=NotesOut)
async def get_notes(video_id: str, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute(
        "SELECT content, updated_at FROM video_notes WHERE video_id = ?", [video_id]
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No notes for this video")
    return NotesOut(video_id=video_id, content=row["content"], updated_at=row["updated_at"])


@router.put("/videos/{video_id}/notes", response_model=NotesOut)
async def upsert_notes(
    video_id: str, body: NotesUpsert, db: aiosqlite.Connection = Depends(get_db)
):
    await db.execute("""
        INSERT INTO video_notes (video_id, content) VALUES (?, ?)
        ON CONFLICT(video_id) DO UPDATE SET content = excluded.content, updated_at = CURRENT_TIMESTAMP
    """, [video_id, body.content])
    await db.commit()
    async with db.execute(
        "SELECT content, updated_at FROM video_notes WHERE video_id = ?", [video_id]
    ) as cursor:
        row = await cursor.fetchone()
    return NotesOut(video_id=video_id, content=row["content"], updated_at=row["updated_at"])
