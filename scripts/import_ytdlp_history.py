#!/usr/bin/env python3
"""
Import YouTube watch history from yt-dlp flat-playlist JSONL dump.

Usage:
    yt-dlp --cookies-from-browser safari --flat-playlist --no-simulate \
        --playlist-end 200 --dump-json "https://www.youtube.com/feed/history" \
        > history.jsonl

    python scripts/import_ytdlp_history.py history.jsonl -d youtube_history.db

Channel info is fetched via YouTube's oEmbed API (no API key required).
Uses async HTTP for speed — 200 videos in a few seconds.
"""

import asyncio
import json
import re
import sqlite3
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import aiohttp
except ImportError:
    print("Error: aiohttp is required. Install with: pip install aiohttp", file=sys.stderr)
    sys.exit(1)


OEMBED_URL = "https://www.youtube.com/oembed"
CONCURRENCY = 10  # parallel oEmbed requests


def extract_channel_id(channel_url: str) -> str | None:
    """Extract a stable channel ID from a YouTube channel URL."""
    if not channel_url:
        return None
    if m := re.search(r'/channel/([^/?#]+)', channel_url):
        return m.group(1)
    if m := re.search(r'/@([^/?#]+)', channel_url):
        return f'@{m.group(1)}'
    return None


async def fetch_oembed(session: aiohttp.ClientSession, video_url: str) -> dict | None:
    """Fetch channel info for a video via YouTube's oEmbed endpoint."""
    try:
        async with session.get(
            OEMBED_URL,
            params={"url": video_url, "format": "json"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception:
        pass
    return None


async def enrich_with_channel_info(entries: list[dict]) -> list[dict]:
    """Add channel_name and channel_url to entries via oEmbed (async, batched)."""
    sem = asyncio.Semaphore(CONCURRENCY)

    async def fetch_one(entry):
        # Skip if we already have channel info
        if entry.get("channel") and entry.get("channel_url"):
            return entry
        async with sem:
            data = await fetch_oembed(session, entry["webpage_url"])
        if data:
            entry["channel"] = data.get("author_name")
            entry["channel_url"] = data.get("author_url")
        return entry

    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_one(e) for e in entries]
        results = []
        total = len(tasks)
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            result = await coro
            results.append(result)
            print(f"\r  Fetching channel info: {i}/{total}", end="", flush=True, file=sys.stderr)
        print(file=sys.stderr)

    return results


def epoch_to_datetime(epoch: int | None) -> str | None:
    """Convert Unix timestamp to ISO datetime string."""
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id   TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_url  TEXT NOT NULL,
            first_seen   TEXT,
            last_seen    TEXT,
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS videos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id   TEXT NOT NULL,
            video_url  TEXT NOT NULL,
            video_title TEXT NOT NULL,
            channel_id TEXT,
            watched_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
            UNIQUE(video_id, watched_at)
        );
        CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id);
        CREATE INDEX IF NOT EXISTS idx_videos_watched  ON videos(watched_at);
        CREATE INDEX IF NOT EXISTS idx_channels_name   ON channels(channel_name);
    """)
    conn.commit()


def upsert_channel(cursor: sqlite3.Cursor, channel_id: str, name: str, url: str, seen_at: str | None):
    cursor.execute("""
        INSERT INTO channels (channel_id, channel_name, channel_url, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            channel_name = excluded.channel_name,
            channel_url  = excluded.channel_url,
            first_seen   = MIN(COALESCE(channels.first_seen, excluded.first_seen), COALESCE(excluded.first_seen, channels.first_seen)),
            last_seen    = MAX(COALESCE(channels.last_seen,  excluded.last_seen),  COALESCE(excluded.last_seen,  channels.last_seen)),
            updated_at   = CURRENT_TIMESTAMP
    """, (channel_id, name, url, seen_at, seen_at))


def import_entries(conn: sqlite3.Connection, entries: list[dict]) -> dict:
    cursor = conn.cursor()
    stats = {"channels_added": 0, "videos_added": 0, "videos_skipped": 0, "no_channel": 0}

    for entry in entries:
        video_id    = entry.get("id")
        video_url   = entry.get("webpage_url", f"https://www.youtube.com/watch?v={video_id}")
        video_title = entry.get("title", "")
        channel_name = entry.get("channel") or entry.get("uploader")
        channel_url  = entry.get("channel_url") or entry.get("uploader_url")
        # epoch is when the dump was created; yt-dlp flat-playlist has no watch timestamp
        watched_at  = epoch_to_datetime(entry.get("epoch")) or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        channel_id = None
        if channel_name and channel_url:
            channel_id = extract_channel_id(channel_url)
            if channel_id:
                upsert_channel(cursor, channel_id, channel_name, channel_url, watched_at)
                stats["channels_added"] += 1
        else:
            stats["no_channel"] += 1

        try:
            cursor.execute("""
                INSERT INTO videos (video_id, video_url, video_title, channel_id, watched_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(video_id, watched_at) DO NOTHING
            """, (video_id, video_url, video_title, channel_id, watched_at))
            if cursor.rowcount > 0:
                stats["videos_added"] += 1
            else:
                stats["videos_skipped"] += 1
        except sqlite3.Error as e:
            print(f"Warning: could not insert {video_id}: {e}", file=sys.stderr)

    conn.commit()
    return stats


def load_jsonl(path: Path) -> list[dict]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: skipping line {lineno}: {e}", file=sys.stderr)
    return entries


def main():
    parser = argparse.ArgumentParser(
        description="Import yt-dlp flat-playlist JSONL into SQLite, enriching with channel info via oEmbed."
    )
    parser.add_argument("input_file", help="JSONL file from yt-dlp --dump-json")
    parser.add_argument("-d", "--database", default="youtube_history.db", help="SQLite database path")
    parser.add_argument("--no-enrich", action="store_true", help="Skip oEmbed channel enrichment")
    args = parser.parse_args()

    if not Path(args.input_file).exists():
        print(f"Error: '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {args.input_file}...", file=sys.stderr)
    entries = load_jsonl(Path(args.input_file))
    print(f"Loaded {len(entries)} entries", file=sys.stderr)

    if not args.no_enrich:
        missing = sum(1 for e in entries if not (e.get("channel") and e.get("channel_url")))
        if missing:
            print(f"Fetching channel info for {missing} videos via oEmbed...", file=sys.stderr)
            entries = asyncio.run(enrich_with_channel_info(entries))
        else:
            print("All entries already have channel info, skipping oEmbed.", file=sys.stderr)

    print(f"Connecting to {args.database}...", file=sys.stderr)
    conn = sqlite3.connect(args.database)
    ensure_schema(conn)

    print("Importing...", file=sys.stderr)
    stats = import_entries(conn, entries)
    conn.close()

    print("\n" + "=" * 50, file=sys.stderr)
    print("IMPORT COMPLETE", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(f"  Videos added:    {stats['videos_added']}", file=sys.stderr)
    print(f"  Videos skipped:  {stats['videos_skipped']} (duplicates)", file=sys.stderr)
    print(f"  Channel upserts: {stats['channels_added']}", file=sys.stderr)
    print(f"  No channel info: {stats['no_channel']}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)


if __name__ == "__main__":
    main()
