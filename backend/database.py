"""
SQLite connection management and schema migrations.
Uses aiosqlite for async access compatible with FastAPI's event loop.
"""

import aiosqlite
import os
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent.parent / "youtube_history.db"))

# New tables to add on top of the existing schema
MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS tags (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL UNIQUE,
        color      TEXT NOT NULL DEFAULT '#6366f1',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",

    """INSERT OR IGNORE INTO tags (name, color) VALUES
        ('reference',   '#3b82f6'),
        ('to-rewatch',  '#f59e0b'),
        ('to-download', '#10b981'),
        ('learning',    '#8b5cf6'),
        ('favorite',    '#ef4444')""",

    """CREATE TABLE IF NOT EXISTS video_tags (
        video_id   TEXT NOT NULL,
        tag_id     INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (video_id, tag_id),
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )""",

    """CREATE TABLE IF NOT EXISTS watchlist (
        video_id   TEXT PRIMARY KEY,
        status     TEXT NOT NULL DEFAULT 'to-rewatch',
        notes      TEXT,
        priority   INTEGER NOT NULL DEFAULT 0,
        added_at   TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        CHECK (status IN ('to-rewatch', 'reference', 'to-download', 'in-progress', 'done'))
    )""",

    """CREATE TABLE IF NOT EXISTS video_notes (
        video_id   TEXT PRIMARY KEY,
        content    TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",

    # Ensure transcripts table exists (may already exist from fetch_transcripts.py)
    """CREATE TABLE IF NOT EXISTS transcripts (
        video_id   TEXT PRIMARY KEY,
        transcript TEXT NOT NULL,
        language   TEXT,
        fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (video_id) REFERENCES videos(video_id)
    )""",
]


async def get_db() -> aiosqlite.Connection:
    """Dependency: yield a DB connection per request."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
    finally:
        await db.close()


async def run_migrations():
    """Run all migrations on startup. Safe to call multiple times (idempotent)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        for sql in MIGRATIONS:
            await db.execute(sql)
        await db.commit()
