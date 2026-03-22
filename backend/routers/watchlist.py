"""
Watchlist CRUD endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
import aiosqlite

from database import get_db
from models import WatchlistItem, WatchlistCreate, WatchlistUpdate

router = APIRouter()

VALID_STATUSES = {"to-rewatch", "reference", "to-download", "in-progress", "done"}


def _validate_status(status: Optional[str]):
    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )


@router.get("/watchlist", response_model=list[WatchlistItem])
async def list_watchlist(
    status: Optional[str] = None,
    sort: str = Query("added_at", pattern="^(priority|added_at|title)$"),
    db: aiosqlite.Connection = Depends(get_db),
):
    _validate_status(status)
    conditions = []
    params = []

    if status:
        conditions.append("w.status = ?")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sort_map = {
        "priority": "w.priority DESC, w.added_at DESC",
        "added_at": "w.added_at DESC",
        "title": "v.video_title ASC",
    }
    order_sql = sort_map.get(sort, "w.added_at DESC")

    async with db.execute(f"""
        SELECT
            w.video_id, w.status, w.notes, w.priority, w.added_at, w.updated_at,
            v.video_title, v.video_url,
            c.channel_name,
            GROUP_CONCAT(DISTINCT t.name) as tags
        FROM watchlist w
        JOIN videos v ON w.video_id = v.video_id
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        LEFT JOIN video_tags vt ON w.video_id = vt.video_id
        LEFT JOIN tags t ON vt.tag_id = t.id
        {where_sql}
        GROUP BY w.video_id
        ORDER BY {order_sql}
    """, params) as cursor:
        rows = await cursor.fetchall()

    return [
        WatchlistItem(
            video_id=r["video_id"],
            status=r["status"],
            notes=r["notes"],
            priority=r["priority"],
            added_at=r["added_at"],
            updated_at=r["updated_at"],
            video_title=r["video_title"],
            video_url=r["video_url"],
            channel_name=r["channel_name"],
            tags=r["tags"].split(",") if r["tags"] else [],
        )
        for r in rows
    ]


@router.post("/watchlist", response_model=WatchlistItem, status_code=201)
async def add_to_watchlist(
    body: WatchlistCreate, db: aiosqlite.Connection = Depends(get_db)
):
    _validate_status(body.status)

    # Verify video exists
    async with db.execute(
        "SELECT video_id FROM videos WHERE video_id = ? LIMIT 1", [body.video_id]
    ) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Video not found in history")

    await db.execute("""
        INSERT INTO watchlist (video_id, status, notes, priority)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            status = excluded.status,
            notes = excluded.notes,
            priority = excluded.priority,
            updated_at = CURRENT_TIMESTAMP
    """, [body.video_id, body.status, body.notes, body.priority])
    await db.commit()

    async with db.execute(
        "SELECT * FROM watchlist WHERE video_id = ?", [body.video_id]
    ) as cursor:
        row = await cursor.fetchone()

    return WatchlistItem(
        video_id=row["video_id"],
        status=row["status"],
        notes=row["notes"],
        priority=row["priority"],
        added_at=row["added_at"],
        updated_at=row["updated_at"],
    )


@router.patch("/watchlist/{video_id}", response_model=WatchlistItem)
async def update_watchlist(
    video_id: str, body: WatchlistUpdate, db: aiosqlite.Connection = Depends(get_db)
):
    _validate_status(body.status)

    async with db.execute(
        "SELECT * FROM watchlist WHERE video_id = ?", [video_id]
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Not in watchlist")

    status = body.status if body.status is not None else row["status"]
    notes = body.notes if body.notes is not None else row["notes"]
    priority = body.priority if body.priority is not None else row["priority"]

    await db.execute("""
        UPDATE watchlist SET status = ?, notes = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
        WHERE video_id = ?
    """, [status, notes, priority, video_id])
    await db.commit()

    async with db.execute("SELECT * FROM watchlist WHERE video_id = ?", [video_id]) as cursor:
        updated = await cursor.fetchone()

    return WatchlistItem(
        video_id=updated["video_id"],
        status=updated["status"],
        notes=updated["notes"],
        priority=updated["priority"],
        added_at=updated["added_at"],
        updated_at=updated["updated_at"],
    )


@router.delete("/watchlist/{video_id}", status_code=204)
async def remove_from_watchlist(
    video_id: str, db: aiosqlite.Connection = Depends(get_db)
):
    async with db.execute(
        "SELECT video_id FROM watchlist WHERE video_id = ?", [video_id]
    ) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Not in watchlist")
    await db.execute("DELETE FROM watchlist WHERE video_id = ?", [video_id])
    await db.commit()
