#!/usr/bin/env python3
"""
Import YouTube watch history into SQLite database.

Handles deduplication automatically - safe to run multiple times with
overlapping data. Ideal for scheduled imports of periodic exports.
"""

import sqlite3
import re
import argparse
import sys
import html
from datetime import datetime
from pathlib import Path


def create_database(db_path):
    """Create database tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Channels table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_url TEXT NOT NULL,
            first_seen TEXT,
            last_seen TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Videos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            video_url TEXT NOT NULL,
            video_title TEXT NOT NULL,
            channel_id TEXT,
            watched_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
            UNIQUE(video_id, watched_at)
        )
    ''')

    # Posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL,
            post_url TEXT NOT NULL,
            post_title TEXT NOT NULL,
            channel_id TEXT,
            viewed_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
            UNIQUE(post_id, viewed_at)
        )
    ''')

    # Create indexes for better query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_watched ON videos(watched_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_channel ON posts(channel_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_viewed ON posts(viewed_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_channels_name ON channels(channel_name)')

    conn.commit()
    return conn


def extract_channel_id(channel_url):
    """Extract channel ID from URL."""
    # Handle /channel/UC... format
    if '/channel/' in channel_url:
        match = re.search(r'/channel/([^/\?]+)', channel_url)
        if match:
            return match.group(1)
    # Handle /@username format
    elif '/@' in channel_url:
        match = re.search(r'/@([^/\?]+)', channel_url)
        if match:
            return f'@{match.group(1)}'
    return None


def parse_timestamp(timestamp_str):
    """Convert Google's timestamp format to ISO format."""
    try:
        # Parse: "Jan 10, 2026, 12:28:55 AM EST"
        # Remove timezone for simplicity (you can enhance this if needed)
        timestamp_str = re.sub(r'\s+[A-Z]{3,4}$', '', timestamp_str)
        dt = datetime.strptime(timestamp_str, '%b %d, %Y, %I:%M:%S %p')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Warning: Could not parse timestamp '{timestamp_str}': {e}", file=sys.stderr)
        return timestamp_str


def extract_entries(html_content):
    """Extract videos, posts, and channels from HTML."""
    videos = []
    posts = []
    channels = {}

    # Pattern to match each outer-cell div block
    outer_cell_pattern = r'<div class="outer-cell[^>]*>.*?(?=<div class="outer-cell|$)'
    entries = re.finditer(outer_cell_pattern, html_content, re.DOTALL)

    for entry_match in entries:
        entry_html = entry_match.group(0)

        # Extract timestamp
        timestamp_pattern = r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+[A-Z]{3,4})'
        timestamp_match = re.search(timestamp_pattern, entry_html)
        timestamp = parse_timestamp(timestamp_match.group(1)) if timestamp_match else None

        # Check for video (Watched)
        video_pattern = r'Watched\s*<a href="(https://www\.youtube\.com/watch\?v=([^"]+))">([^<]+)</a>'
        video_match = re.search(video_pattern, entry_html)

        # Check for post (Viewed)
        post_pattern = r'Viewed\s*<a href="(https://www\.youtube\.com/post/([^"]+))">([^<]+)</a>'
        post_match = re.search(post_pattern, entry_html)

        # Extract channel
        channel_pattern = r'<a href="(https://www\.youtube\.com/(channel/[^"]+|@[^"]+))">([^<]+)</a>'
        channel_matches = re.findall(channel_pattern, entry_html)

        channel_url = ""
        channel_name = ""
        channel_id = None

        if channel_matches:
            channel_url = channel_matches[0][0]
            channel_name = html.unescape(channel_matches[0][2])
            channel_id = extract_channel_id(channel_url)

            # Track channel
            if channel_id and channel_id not in channels:
                channels[channel_id] = {
                    'name': channel_name,
                    'url': channel_url,
                    'first_seen': timestamp,
                    'last_seen': timestamp
                }
            elif channel_id and timestamp:
                # Update last_seen
                if not channels[channel_id]['first_seen'] or timestamp < channels[channel_id]['first_seen']:
                    channels[channel_id]['first_seen'] = timestamp
                if not channels[channel_id]['last_seen'] or timestamp > channels[channel_id]['last_seen']:
                    channels[channel_id]['last_seen'] = timestamp

        if video_match:
            videos.append({
                'video_id': video_match.group(2),
                'video_url': video_match.group(1),
                'video_title': html.unescape(video_match.group(3)),
                'channel_id': channel_id,
                'channel_name': channel_name,
                'channel_url': channel_url,
                'watched_at': timestamp
            })

        elif post_match:
            posts.append({
                'post_id': post_match.group(2),
                'post_url': post_match.group(1),
                'post_title': html.unescape(post_match.group(3)),
                'channel_id': channel_id,
                'channel_name': channel_name,
                'channel_url': channel_url,
                'viewed_at': timestamp
            })

    return videos, posts, channels


def import_to_database(conn, videos, posts, channels, verbose=False):
    """Import extracted data into database."""
    cursor = conn.cursor()

    stats = {
        'channels_added': 0,
        'channels_updated': 0,
        'videos_added': 0,
        'videos_skipped': 0,
        'posts_added': 0,
        'posts_skipped': 0
    }

    # Import channels first
    for channel_id, info in channels.items():
        try:
            cursor.execute('''
                INSERT INTO channels (channel_id, channel_name, channel_url, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    channel_name = excluded.channel_name,
                    channel_url = excluded.channel_url,
                    first_seen = MIN(channels.first_seen, excluded.first_seen),
                    last_seen = MAX(channels.last_seen, excluded.last_seen),
                    updated_at = CURRENT_TIMESTAMP
            ''', (channel_id, info['name'], info['url'], info['first_seen'], info['last_seen']))

            if cursor.rowcount > 0:
                if cursor.lastrowid > 0:
                    stats['channels_added'] += 1
                else:
                    stats['channels_updated'] += 1
        except sqlite3.Error as e:
            if verbose:
                print(f"Warning: Could not insert channel {channel_id}: {e}", file=sys.stderr)

    # Import videos
    for video in videos:
        try:
            cursor.execute('''
                INSERT INTO videos (video_id, video_url, video_title, channel_id, watched_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(video_id, watched_at) DO UPDATE SET
                    channel_id = COALESCE(videos.channel_id, excluded.channel_id),
                    video_title = COALESCE(excluded.video_title, videos.video_title)
            ''', (video['video_id'], video['video_url'], video['video_title'],
                  video['channel_id'], video['watched_at']))

            if cursor.rowcount > 0:
                stats['videos_added'] += 1
            else:
                stats['videos_skipped'] += 1
        except sqlite3.Error as e:
            if verbose:
                print(f"Warning: Could not insert video {video['video_id']}: {e}", file=sys.stderr)

    # Import posts
    for post in posts:
        try:
            cursor.execute('''
                INSERT INTO posts (post_id, post_url, post_title, channel_id, viewed_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(post_id, viewed_at) DO NOTHING
            ''', (post['post_id'], post['post_url'], post['post_title'],
                  post['channel_id'], post['viewed_at']))

            if cursor.rowcount > 0:
                stats['posts_added'] += 1
            else:
                stats['posts_skipped'] += 1
        except sqlite3.Error as e:
            if verbose:
                print(f"Warning: Could not insert post {post['post_id']}: {e}", file=sys.stderr)

    conn.commit()
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Import YouTube watch history HTML into SQLite database'
    )
    parser.add_argument(
        'input_file',
        help='Input HTML file from YouTube watch history export'
    )
    parser.add_argument(
        '-d', '--database',
        help='Database file path (default: youtube_history.db)',
        default='youtube_history.db'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Check if input file exists
    if not Path(args.input_file).exists():
        print(f"Error: File '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {args.input_file}...", file=sys.stderr)

    # Read HTML
    with open(args.input_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    print("Extracting entries...", file=sys.stderr)
    videos, posts, channels = extract_entries(html_content)

    print(f"Found {len(videos)} videos", file=sys.stderr)
    print(f"Found {len(posts)} posts", file=sys.stderr)
    print(f"Found {len(channels)} unique channels", file=sys.stderr)

    # Create/connect to database
    print(f"\nConnecting to database: {args.database}", file=sys.stderr)
    conn = create_database(args.database)

    # Import data
    print("Importing data...", file=sys.stderr)
    stats = import_to_database(conn, videos, posts, channels, args.verbose)

    # Print statistics
    print("\n" + "="*60, file=sys.stderr)
    print("IMPORT COMPLETE", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print(f"Channels added:   {stats['channels_added']}", file=sys.stderr)
    print(f"Channels updated: {stats['channels_updated']}", file=sys.stderr)
    print(f"Videos added:     {stats['videos_added']}", file=sys.stderr)
    print(f"Videos skipped:   {stats['videos_skipped']} (duplicates)", file=sys.stderr)
    print(f"Posts added:      {stats['posts_added']}", file=sys.stderr)
    print(f"Posts skipped:    {stats['posts_skipped']} (duplicates)", file=sys.stderr)
    print("="*60, file=sys.stderr)

    # Get total counts
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM videos')
    total_videos = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM posts')
    total_posts = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM channels')
    total_channels = cursor.fetchone()[0]

    print(f"\nTotal in database:", file=sys.stderr)
    print(f"  Videos:   {total_videos}", file=sys.stderr)
    print(f"  Posts:    {total_posts}", file=sys.stderr)
    print(f"  Channels: {total_channels}", file=sys.stderr)

    conn.close()
    print(f"\nDatabase saved to: {args.database}", file=sys.stderr)


if __name__ == '__main__':
    main()
