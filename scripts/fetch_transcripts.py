#!/usr/bin/env python3
"""
Fetch YouTube video transcripts and store them in the database.

This script can fetch transcripts for videos in your history database.
Requires: pip install youtube-transcript-api

Note: Not all videos have transcripts available. The script will skip
videos without transcripts or with disabled captions.

Don't run this for lots of urls because youtube could ban you or your ip

"""

import sqlite3
import argparse
import sys
import time
from pathlib import Path

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable
    )
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False
    print("Warning: youtube-transcript-api not installed", file=sys.stderr)
    print("Install with: pip install youtube-transcript-api", file=sys.stderr)


def setup_transcript_table(conn):
    """Create transcripts table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcripts (
            video_id TEXT PRIMARY KEY,
            transcript TEXT NOT NULL,
            language TEXT,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    ''')
    conn.commit()


def get_videos_without_transcripts(conn, limit=None):
    """Get videos that don't have transcripts yet."""
    cursor = conn.cursor()

    query = '''
        SELECT DISTINCT v.video_id, v.video_title, c.channel_name
        FROM videos v
        LEFT JOIN transcripts t ON v.video_id = t.video_id
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        WHERE t.video_id IS NULL
        ORDER BY v.watched_at DESC
    '''

    if limit:
        query += f' LIMIT {limit}'

    cursor.execute(query)
    return cursor.fetchall()


def fetch_transcript(video_id, languages=None):
    """Fetch transcript for a video."""
    if not TRANSCRIPT_API_AVAILABLE:
        raise ImportError("youtube-transcript-api not installed")

    if languages is None:
        languages = ['en', 'en-US', 'en-GB']

    try:
        # Try to get transcript in preferred languages
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try manual captions first (more accurate)
        try:
            for lang in languages:
                try:
                    transcript = transcript_list.find_manually_created_transcript([lang])
                    text = ' '.join([entry['text'] for entry in transcript.fetch()])
                    return text, lang, 'manual'
                except NoTranscriptFound:
                    continue
        except:
            pass

        # Fall back to auto-generated captions
        try:
            for lang in languages:
                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    text = ' '.join([entry['text'] for entry in transcript.fetch()])
                    return text, lang, 'auto'
                except NoTranscriptFound:
                    continue
        except:
            pass

        # Try any available transcript
        transcript = transcript_list.find_transcript(transcript_list._manually_created_transcripts.keys() or
                                                     transcript_list._generated_transcripts.keys())
        text = ' '.join([entry['text'] for entry in transcript.fetch()])
        return text, transcript.language_code, 'any'

    except TranscriptsDisabled:
        raise Exception("Transcripts disabled for this video")
    except NoTranscriptFound:
        raise Exception("No transcript found")
    except VideoUnavailable:
        raise Exception("Video unavailable")
    except Exception as e:
        raise Exception(f"Error fetching transcript: {str(e)}")


def save_transcript(conn, video_id, transcript, language):
    """Save transcript to database."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO transcripts (video_id, transcript, language)
        VALUES (?, ?, ?)
    ''', (video_id, transcript, language))
    conn.commit()


def search_transcripts(conn, search_term):
    """Search for videos by transcript content."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            v.video_title,
            c.channel_name,
            v.video_url,
            v.watched_at,
            substr(t.transcript, 1, 200) as preview
        FROM transcripts t
        JOIN videos v ON t.video_id = v.video_id
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        WHERE t.transcript LIKE ?
        ORDER BY v.watched_at DESC
        LIMIT 50
    ''', (f'%{search_term}%',))

    return cursor.fetchall()


def export_transcript(conn, video_id, output_file):
    """Export a single transcript to file."""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.video_title, c.channel_name, v.video_url, t.transcript
        FROM transcripts t
        JOIN videos v ON t.video_id = v.video_id
        LEFT JOIN channels c ON v.channel_id = c.channel_id
        WHERE v.video_id = ?
    ''', (video_id,))

    row = cursor.fetchone()
    if not row:
        print(f"No transcript found for video {video_id}", file=sys.stderr)
        return False

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Title: {row[0]}\n")
        f.write(f"Channel: {row[1]}\n")
        f.write(f"URL: {row[2]}\n")
        f.write(f"\n{'='*60}\n\n")
        f.write(row[3])

    print(f"Transcript exported to {output_file}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Fetch and manage YouTube video transcripts'
    )
    parser.add_argument(
        '-d', '--database',
        help='Database file path (default: youtube_history.db)',
        default='youtube_history.db'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch transcripts for videos')
    fetch_parser.add_argument(
        '-n', '--limit',
        type=int,
        help='Number of videos to process (default: all without transcripts)',
        default=None
    )
    fetch_parser.add_argument(
        '-l', '--languages',
        help='Comma-separated list of language codes (default: en,en-US)',
        default='en,en-US'
    )
    fetch_parser.add_argument(
        '--delay',
        type=float,
        help='Delay between requests in seconds (default: 1)',
        default=1.0
    )

    # Search command
    search_parser = subparsers.add_parser('search', help='Search transcripts')
    search_parser.add_argument('term', help='Search term')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export transcript to file')
    export_parser.add_argument('video_id', help='Video ID')
    export_parser.add_argument('output', help='Output file path')

    # Stats command
    subparsers.add_parser('stats', help='Show transcript statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Check if database exists
    if not Path(args.database).exists():
        print(f"Error: Database '{args.database}' not found", file=sys.stderr)
        print("Run import_to_db.py first to create the database", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(args.database)
    conn.row_factory = sqlite3.Row

    # Setup transcript table
    setup_transcript_table(conn)

    try:
        if args.command == 'fetch':
            if not TRANSCRIPT_API_AVAILABLE:
                print("\nError: youtube-transcript-api not installed", file=sys.stderr)
                print("Install with: pip install youtube-transcript-api", file=sys.stderr)
                sys.exit(1)

            languages = args.languages.split(',')
            videos = get_videos_without_transcripts(conn, args.limit)

            if not videos:
                print("No videos without transcripts found!")
                return

            print(f"Found {len(videos)} videos without transcripts")
            print(f"Fetching transcripts (delay: {args.delay}s between requests)...\n")

            success = 0
            failed = 0
            skipped = 0

            for i, video in enumerate(videos, 1):
                video_id = video['video_id']
                title = video['video_title'][:50]
                channel = video['channel_name'] or 'Unknown'

                print(f"[{i}/{len(videos)}] {title} ({channel})... ", end='', flush=True)

                try:
                    transcript, language, source = fetch_transcript(video_id, languages)
                    save_transcript(conn, video_id, transcript, language)
                    print(f"✓ ({language}, {source})")
                    success += 1
                except Exception as e:
                    print(f"✗ {str(e)}")
                    failed += 1

                # Rate limiting
                if i < len(videos):
                    time.sleep(args.delay)

            print(f"\n{'='*60}")
            print(f"Results:")
            print(f"  Success: {success}")
            print(f"  Failed:  {failed}")
            print(f"{'='*60}")

        elif args.command == 'search':
            results = search_transcripts(conn, args.term)

            if not results:
                print(f"No videos found containing '{args.term}'")
                return

            print(f"\nFound {len(results)} videos containing '{args.term}':\n")
            print("="*100)

            for row in results:
                print(f"Title:   {row['video_title']}")
                print(f"Channel: {row['channel_name'] or 'Unknown'}")
                print(f"URL:     {row['video_url']}")
                print(f"Watched: {row['watched_at']}")
                print(f"Preview: {row['preview']}...")
                print("-"*100)

        elif args.command == 'export':
            export_transcript(conn, args.video_id, args.output)

        elif args.command == 'stats':
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM videos')
            total_videos = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM transcripts')
            total_transcripts = cursor.fetchone()[0]

            cursor.execute('SELECT language, COUNT(*) as count FROM transcripts GROUP BY language ORDER BY count DESC')
            languages = cursor.fetchall()

            print("\nTranscript Statistics:")
            print("="*60)
            print(f"Total Videos:        {total_videos:,}")
            print(f"With Transcripts:    {total_transcripts:,}")
            print(f"Without Transcripts: {total_videos - total_transcripts:,}")
            print(f"Coverage:            {total_transcripts/total_videos*100:.1f}%")

            if languages:
                print("\nLanguages:")
                for lang in languages:
                    print(f"  {lang['language']}: {lang['count']}")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
