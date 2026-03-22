#!/usr/bin/env python3
"""
Query and analyze YouTube watch history database.

Provides common queries and statistics about your viewing habits.
"""

import sqlite3
import argparse
import sys
from datetime import datetime, timedelta


def connect_db(db_path):
    """Connect to database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)


def print_table(headers, rows, widths=None):
    """Print a nicely formatted table."""
    if not rows:
        print("No results found.")
        return

    # Auto-calculate widths if not provided
    if widths is None:
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))

    # Print header
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("-" * len(header_line))

    # Print rows
    for row in rows:
        print(" | ".join(str(cell).ljust(w) for cell, w in zip(row, widths)))


def top_channels(conn, limit=20):
    """Show most watched channels."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            c.channel_name,
            COUNT(v.id) as video_count,
            COUNT(p.id) as post_count,
            COUNT(v.id) + COUNT(p.id) as total_interactions,
            c.first_seen,
            c.last_seen
        FROM channels c
        LEFT JOIN videos v ON c.channel_id = v.channel_id
        LEFT JOIN posts p ON c.channel_id = p.channel_id
        GROUP BY c.channel_id
        ORDER BY total_interactions DESC
        LIMIT ?
    ''', (limit,))

    rows = cursor.fetchall()
    print(f"\nTop {limit} Most Watched Channels:")
    print("="*100)

    data = []
    for i, row in enumerate(rows, 1):
        data.append([
            f"{i}.",
            row['channel_name'][:40],
            str(row['video_count']),
            str(row['post_count']),
            str(row['total_interactions'])
        ])

    print_table(['#', 'Channel', 'Videos', 'Posts', 'Total'], data)


def recent_activity(conn, days=7):
    """Show recent viewing activity."""
    cursor = conn.cursor()

    # Get date threshold
    threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    cursor.execute('''
        SELECT
            video_title as title,
            'Video' as type,
            watched_at as timestamp,
            c.channel_name
        FROM videos v
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        WHERE watched_at >= ?
        UNION ALL
        SELECT
            post_title as title,
            'Post' as type,
            viewed_at as timestamp,
            c.channel_name
        FROM posts p
        LEFT JOIN channels c ON p.channel_id = c.channel_id
        WHERE viewed_at >= ?
        ORDER BY timestamp DESC
    ''', (threshold, threshold))

    rows = cursor.fetchall()
    print(f"\nActivity in Last {days} Days:")
    print("="*100)

    if not rows:
        print(f"No activity found in the last {days} days.")
        return

    data = []
    for row in rows:
        data.append([
            row['type'],
            row['title'][:50],
            row['channel_name'][:25] if row['channel_name'] else 'Unknown',
            row['timestamp']
        ])

    print_table(['Type', 'Title', 'Channel', 'Timestamp'], data)
    print(f"\nTotal: {len(rows)} items")


def viewing_stats(conn):
    """Show overall viewing statistics."""
    cursor = conn.cursor()

    # Total counts
    cursor.execute('SELECT COUNT(*) FROM videos')
    total_videos = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM posts')
    total_posts = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM channels')
    total_channels = cursor.fetchone()[0]

    # Date range
    cursor.execute('SELECT MIN(watched_at), MAX(watched_at) FROM videos')
    video_range = cursor.fetchone()

    # Most active day
    cursor.execute('''
        SELECT DATE(watched_at) as day, COUNT(*) as count
        FROM videos
        GROUP BY DATE(watched_at)
        ORDER BY count DESC
        LIMIT 1
    ''')
    most_active = cursor.fetchone()

    # Average per day
    cursor.execute('''
        SELECT
            COUNT(*) * 1.0 / COUNT(DISTINCT DATE(watched_at)) as avg_per_day
        FROM videos
        WHERE watched_at IS NOT NULL
    ''')
    avg_per_day = cursor.fetchone()[0]

    print("\nViewing Statistics:")
    print("="*60)
    print(f"Total Videos Watched:     {total_videos:,}")
    print(f"Total Posts Viewed:       {total_posts:,}")
    print(f"Total Channels:           {total_channels:,}")
    print(f"\nFirst Video:              {video_range[0]}")
    print(f"Most Recent:              {video_range[1]}")
    if most_active:
        print(f"\nMost Active Day:          {most_active['day']} ({most_active['count']} videos)")
    if avg_per_day:
        print(f"Average Videos Per Day:   {avg_per_day:.1f}")


def search_videos(conn, search_term):
    """Search for videos by title or channel."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            v.video_title,
            c.channel_name,
            v.watched_at,
            v.video_url
        FROM videos v
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        WHERE v.video_title LIKE ? OR c.channel_name LIKE ?
        ORDER BY v.watched_at DESC
        LIMIT 50
    ''', (f'%{search_term}%', f'%{search_term}%'))

    rows = cursor.fetchall()
    print(f"\nSearch Results for '{search_term}':")
    print("="*100)

    if not rows:
        print("No results found.")
        return

    data = []
    for row in rows:
        data.append([
            row['video_title'][:50],
            row['channel_name'][:25] if row['channel_name'] else 'Unknown',
            row['watched_at']
        ])

    print_table(['Title', 'Channel', 'Watched'], data)
    print(f"\nShowing {len(rows)} results (max 50)")


def channel_timeline(conn, channel_name):
    """Show viewing timeline for a specific channel."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            video_title,
            watched_at,
            video_url
        FROM videos v
        JOIN channels c ON v.channel_id = c.channel_id
        WHERE c.channel_name LIKE ?
        ORDER BY watched_at DESC
        LIMIT 100
    ''', (f'%{channel_name}%',))

    rows = cursor.fetchall()
    print(f"\nViewing Timeline for '{channel_name}':")
    print("="*100)

    if not rows:
        print("No videos found for this channel.")
        return

    data = []
    for row in rows:
        data.append([
            row['video_title'][:60],
            row['watched_at']
        ])

    print_table(['Title', 'Watched'], data)
    print(f"\nShowing {len(rows)} most recent videos (max 100)")


def export_csv(conn, output_file):
    """Export all data to CSV."""
    import csv

    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            v.video_title,
            v.video_url,
            c.channel_name,
            c.channel_url,
            v.watched_at
        FROM videos v
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        ORDER BY v.watched_at DESC
    ''')

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Title', 'Video URL', 'Channel', 'Channel URL', 'Watched At'])

        for row in cursor:
            writer.writerow([
                row['video_title'],
                row['video_url'],
                row['channel_name'] or '',
                row['channel_url'] or '',
                row['watched_at']
            ])

    print(f"\nData exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Query YouTube watch history database'
    )
    parser.add_argument(
        '-d', '--database',
        help='Database file path (default: youtube_history.db)',
        default='youtube_history.db'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Stats command
    subparsers.add_parser('stats', help='Show overall statistics')

    # Top channels command
    top_parser = subparsers.add_parser('top', help='Show top channels')
    top_parser.add_argument('-n', '--limit', type=int, default=20, help='Number of channels to show')

    # Recent activity command
    recent_parser = subparsers.add_parser('recent', help='Show recent activity')
    recent_parser.add_argument('-d', '--days', type=int, default=7, help='Number of days to look back')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search videos')
    search_parser.add_argument('term', help='Search term')

    # Channel timeline command
    timeline_parser = subparsers.add_parser('channel', help='Show channel timeline')
    timeline_parser.add_argument('name', help='Channel name')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export to CSV')
    export_parser.add_argument('output', help='Output CSV file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    conn = connect_db(args.database)

    try:
        if args.command == 'stats':
            viewing_stats(conn)
        elif args.command == 'top':
            top_channels(conn, args.limit)
        elif args.command == 'recent':
            recent_activity(conn, args.days)
        elif args.command == 'search':
            search_videos(conn, args.term)
        elif args.command == 'channel':
            channel_timeline(conn, args.name)
        elif args.command == 'export':
            export_csv(conn, args.output)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
