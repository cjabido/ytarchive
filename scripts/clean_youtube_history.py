#!/usr/bin/env python3
"""
Clean YouTube watch history HTML export by removing CSS bloat
and extracting semantic information.

Uses only Python standard library - no external dependencies needed.
"""

import re
import argparse
import sys
import html


def extract_videos(html_content):
    """
    Extract video information from the HTML using regex patterns.

    Returns a list of dicts with video info.
    """
    videos = []

    # Pattern to match each outer-cell div block
    # Match from outer-cell to the next outer-cell or end of content
    # The pattern captures everything from one outer-cell start to just before the next
    outer_cell_pattern = r'<div class="outer-cell[^>]*>.*?(?=<div class="outer-cell|$)'

    # Find all video entry blocks
    entries = re.finditer(outer_cell_pattern, html_content, re.DOTALL)

    for entry_match in entries:
        entry_html = entry_match.group(0)

        # Extract video URL and title
        # Note: There's a non-breaking space (\xa0 or &nbsp;) between "Watched" and the link
        video_pattern = r'Watched\s*<a href="(https://www\.youtube\.com/watch\?v=([^"]+))">([^<]+)</a>'
        video_match = re.search(video_pattern, entry_html)

        if not video_match:
            continue

        video_url = video_match.group(1)
        video_id = video_match.group(2)
        video_title = html.unescape(video_match.group(3))

        # Extract channel URL and name
        # Can be either /channel/ or /@username format
        channel_pattern = r'<a href="(https://www\.youtube\.com/(channel/[^"]+|@[^"]+))">([^<]+)</a>'
        channel_match = re.search(channel_pattern, entry_html)

        channel_url = ""
        channel_name = ""
        if channel_match:
            channel_url = channel_match.group(1)
            # Group 3 has the channel name (group 2 is the path part)
            channel_name = html.unescape(channel_match.group(3))

        # Extract timestamp - it's typically after the channel link
        # Look for a date pattern like "Jan 10, 2026, 12:28:55 AM EST"
        timestamp_pattern = r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+[A-Z]{3,4})'
        timestamp_match = re.search(timestamp_pattern, entry_html)

        timestamp = ""
        if timestamp_match:
            timestamp = timestamp_match.group(1)

        videos.append({
            'video_url': video_url,
            'video_id': video_id,
            'video_title': video_title,
            'channel_url': channel_url,
            'channel_name': channel_name,
            'timestamp': timestamp
        })

    return videos


def generate_clean_html(videos):
    """
    Generate clean HTML from extracted video data.
    """
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <title>YouTube Watch History</title>',
        '  <style>',
        '    body {',
        '      font-family: Arial, sans-serif;',
        '      max-width: 900px;',
        '      margin: 0 auto;',
        '      padding: 20px;',
        '      line-height: 1.6;',
        '    }',
        '    .video-entry {',
        '      border: 1px solid #ddd;',
        '      padding: 15px;',
        '      margin-bottom: 15px;',
        '      border-radius: 5px;',
        '    }',
        '    .video-title {',
        '      font-size: 1.1em;',
        '      font-weight: bold;',
        '      margin-bottom: 5px;',
        '    }',
        '    .channel-name {',
        '      color: #606060;',
        '      margin-bottom: 5px;',
        '    }',
        '    .timestamp {',
        '      color: #909090;',
        '      font-size: 0.9em;',
        '    }',
        '    a {',
        '      color: #065fd4;',
        '      text-decoration: none;',
        '    }',
        '    a:hover {',
        '      text-decoration: underline;',
        '    }',
        '  </style>',
        '</head>',
        '<body>',
        '  <h1>YouTube Watch History</h1>',
    ]

    # Add each video entry
    for video in videos:
        html_parts.extend([
            '  <div class="video-entry">',
            '    <div class="video-title">',
            f'      <a href="{html.escape(video["video_url"])}">{html.escape(video["video_title"])}</a>',
            '    </div>',
        ])

        if video['channel_name']:
            html_parts.extend([
                '    <div class="channel-name">',
                f'      Channel: <a href="{html.escape(video["channel_url"])}">{html.escape(video["channel_name"])}</a>',
                '    </div>',
            ])

        if video['timestamp']:
            html_parts.extend([
                '    <div class="timestamp">',
                f'      {html.escape(video["timestamp"])}',
                '    </div>',
            ])

        html_parts.append('  </div>')

    html_parts.extend([
        '</body>',
        '</html>'
    ])

    return '\n'.join(html_parts)


def clean_youtube_history(input_file, output_file=None):
    """
    Parse YouTube watch history HTML and extract clean semantic information.

    Args:
        input_file: Path to the input HTML file
        output_file: Path to output file (optional, defaults to stdout)
    """
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract video information
    videos = extract_videos(html_content)

    print(f"Found {len(videos)} video entries", file=sys.stderr)

    # Generate clean HTML
    output_html = generate_clean_html(videos)

    # Output the cleaned HTML
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_html)
        print(f"Cleaned HTML written to {output_file}", file=sys.stderr)
    else:
        print(output_html)


def main():
    parser = argparse.ArgumentParser(
        description='Clean YouTube watch history HTML by removing CSS bloat'
    )
    parser.add_argument(
        'input_file',
        help='Input HTML file from YouTube watch history export'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: print to stdout)',
        default=None
    )

    args = parser.parse_args()

    try:
        clean_youtube_history(args.input_file, args.output)
    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
