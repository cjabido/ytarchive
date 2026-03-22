#!/usr/bin/env python3
"""
Extract different types of YouTube history entries:
- Videos (watched videos)
- Posts (community posts viewed)
- Channels (all unique channels encountered)

Uses only Python standard library - no external dependencies needed.
"""

import re
import argparse
import sys
import html


def extract_entries(html_content):
    """
    Extract all entry types from the HTML.

    Returns dicts with videos, posts, and channel references.
    """
    videos = []
    posts = []
    channel_refs = {}  # URL -> {name, count}

    # Pattern to match each outer-cell div block
    outer_cell_pattern = r'<div class="outer-cell[^>]*>.*?(?=<div class="outer-cell|$)'

    # Find all entry blocks
    entries = re.finditer(outer_cell_pattern, html_content, re.DOTALL)

    for entry_match in entries:
        entry_html = entry_match.group(0)

        # Extract timestamp (common to all entry types)
        timestamp_pattern = r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+[A-Z]{3,4})'
        timestamp_match = re.search(timestamp_pattern, entry_html)
        timestamp = timestamp_match.group(1) if timestamp_match else ""

        # Check if this is a video entry (Watched ...)
        video_pattern = r'Watched\s*<a href="(https://www\.youtube\.com/watch\?v=([^"]+))">([^<]+)</a>'
        video_match = re.search(video_pattern, entry_html)

        # Check if this is a post entry (Viewed ... /post/)
        post_pattern = r'Viewed\s*<a href="(https://www\.youtube\.com/post/([^"]+))">([^<]+)</a>'
        post_match = re.search(post_pattern, entry_html)

        # Extract channel information (present in both videos and posts)
        channel_pattern = r'<a href="(https://www\.youtube\.com/(channel/[^"]+|@[^"]+))">([^<]+)</a>'
        channel_matches = re.findall(channel_pattern, entry_html)

        # Process channel references
        for channel_match in channel_matches:
            channel_url = channel_match[0]
            channel_name = html.unescape(channel_match[2])

            if channel_url not in channel_refs:
                channel_refs[channel_url] = {
                    'name': channel_name,
                    'count': 0,
                    'first_seen': timestamp
                }
            channel_refs[channel_url]['count'] += 1
            if timestamp:
                channel_refs[channel_url]['last_seen'] = timestamp

        if video_match:
            # This is a video entry
            video_url = video_match.group(1)
            video_id = video_match.group(2)
            video_title = html.unescape(video_match.group(3))

            # Get the associated channel (usually first channel link)
            channel_url = channel_matches[0][0] if channel_matches else ""
            channel_name = html.unescape(channel_matches[0][2]) if channel_matches else ""

            videos.append({
                'video_url': video_url,
                'video_id': video_id,
                'video_title': video_title,
                'channel_url': channel_url,
                'channel_name': channel_name,
                'timestamp': timestamp
            })

        elif post_match:
            # This is a post entry
            post_url = post_match.group(1)
            post_id = post_match.group(2)
            post_title = html.unescape(post_match.group(3))

            # Get the associated channel
            channel_url = channel_matches[0][0] if channel_matches else ""
            channel_name = html.unescape(channel_matches[0][2]) if channel_matches else ""

            posts.append({
                'post_url': post_url,
                'post_id': post_id,
                'post_title': post_title,
                'channel_url': channel_url,
                'channel_name': channel_name,
                'timestamp': timestamp
            })

    return videos, posts, channel_refs


def generate_videos_html(videos):
    """Generate clean HTML for video entries."""
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <title>YouTube Watch History - Videos</title>',
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
        '  <h1>YouTube Watch History - Videos</h1>',
        f'  <p>Total videos: {len(videos)}</p>',
    ]

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

    html_parts.extend(['</body>', '</html>'])
    return '\n'.join(html_parts)


def generate_posts_html(posts):
    """Generate clean HTML for post entries."""
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <title>YouTube Watch History - Posts</title>',
        '  <style>',
        '    body {',
        '      font-family: Arial, sans-serif;',
        '      max-width: 900px;',
        '      margin: 0 auto;',
        '      padding: 20px;',
        '      line-height: 1.6;',
        '    }',
        '    .post-entry {',
        '      border: 1px solid #ddd;',
        '      padding: 15px;',
        '      margin-bottom: 15px;',
        '      border-radius: 5px;',
        '      background-color: #f9f9f9;',
        '    }',
        '    .post-title {',
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
        '  <h1>YouTube Watch History - Community Posts</h1>',
        f'  <p>Total posts viewed: {len(posts)}</p>',
    ]

    for post in posts:
        html_parts.extend([
            '  <div class="post-entry">',
            '    <div class="post-title">',
            f'      <a href="{html.escape(post["post_url"])}">{html.escape(post["post_title"])}</a>',
            '    </div>',
        ])

        if post['channel_name']:
            html_parts.extend([
                '    <div class="channel-name">',
                f'      Channel: <a href="{html.escape(post["channel_url"])}">{html.escape(post["channel_name"])}</a>',
                '    </div>',
            ])

        if post['timestamp']:
            html_parts.extend([
                '    <div class="timestamp">',
                f'      {html.escape(post["timestamp"])}',
                '    </div>',
            ])

        html_parts.append('  </div>')

    html_parts.extend(['</body>', '</html>'])
    return '\n'.join(html_parts)


def generate_channels_html(channel_refs):
    """Generate clean HTML for channel references."""
    # Sort by count (most frequent first)
    sorted_channels = sorted(
        channel_refs.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )

    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <title>YouTube Watch History - Channels</title>',
        '  <style>',
        '    body {',
        '      font-family: Arial, sans-serif;',
        '      max-width: 1000px;',
        '      margin: 0 auto;',
        '      padding: 20px;',
        '      line-height: 1.6;',
        '    }',
        '    .channel-entry {',
        '      border: 1px solid #ddd;',
        '      padding: 15px;',
        '      margin-bottom: 10px;',
        '      border-radius: 5px;',
        '      display: flex;',
        '      justify-content: space-between;',
        '      align-items: center;',
        '    }',
        '    .channel-info {',
        '      flex: 1;',
        '    }',
        '    .channel-name {',
        '      font-size: 1.1em;',
        '      font-weight: bold;',
        '      margin-bottom: 5px;',
        '    }',
        '    .channel-stats {',
        '      color: #606060;',
        '      font-size: 0.9em;',
        '    }',
        '    .interaction-count {',
        '      font-size: 1.2em;',
        '      font-weight: bold;',
        '      color: #065fd4;',
        '      margin-left: 20px;',
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
        '  <h1>YouTube Watch History - Channels</h1>',
        f'  <p>Total unique channels: {len(channel_refs)}</p>',
        '  <p>Sorted by number of interactions (videos watched + posts viewed)</p>',
    ]

    for channel_url, info in sorted_channels:
        html_parts.extend([
            '  <div class="channel-entry">',
            '    <div class="channel-info">',
            '      <div class="channel-name">',
            f'        <a href="{html.escape(channel_url)}">{html.escape(info["name"])}</a>',
            '      </div>',
            '      <div class="channel-stats">',
        ])

        if 'first_seen' in info and 'last_seen' in info:
            html_parts.append(f'        First: {html.escape(info["first_seen"])} | Last: {html.escape(info["last_seen"])}')
        elif 'first_seen' in info:
            html_parts.append(f'        {html.escape(info["first_seen"])}')

        html_parts.extend([
            '      </div>',
            '    </div>',
            '    <div class="interaction-count">',
            f'      {info["count"]}',
            '    </div>',
            '  </div>',
        ])

    html_parts.extend(['</body>', '</html>'])
    return '\n'.join(html_parts)


def main():
    parser = argparse.ArgumentParser(
        description='Extract videos, posts, and channels from YouTube watch history HTML'
    )
    parser.add_argument(
        'input_file',
        help='Input HTML file from YouTube watch history export'
    )
    parser.add_argument(
        '--videos',
        help='Output file for videos (default: [input]-videos.html)',
        default=None
    )
    parser.add_argument(
        '--posts',
        help='Output file for posts (default: [input]-posts.html)',
        default=None
    )
    parser.add_argument(
        '--channels',
        help='Output file for channels (default: [input]-channels.html)',
        default=None
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Extract all types (videos, posts, channels)'
    )

    args = parser.parse_args()

    # Read the input file
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {args.input_file}...", file=sys.stderr)

    # Extract all entries
    videos, posts, channel_refs = extract_entries(html_content)

    print(f"Found {len(videos)} videos", file=sys.stderr)
    print(f"Found {len(posts)} posts", file=sys.stderr)
    print(f"Found {len(channel_refs)} unique channels", file=sys.stderr)

    # Determine output file names
    base_name = args.input_file.rsplit('.', 1)[0]

    videos_file = args.videos or f"{base_name}-videos.html"
    posts_file = args.posts or f"{base_name}-posts.html"
    channels_file = args.channels or f"{base_name}-channels.html"

    # Generate and write outputs
    if args.all or args.videos:
        html_output = generate_videos_html(videos)
        with open(videos_file, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Videos written to {videos_file}", file=sys.stderr)

    if args.all or args.posts:
        html_output = generate_posts_html(posts)
        with open(posts_file, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Posts written to {posts_file}", file=sys.stderr)

    if args.all or args.channels:
        html_output = generate_channels_html(channel_refs)
        with open(channels_file, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Channels written to {channels_file}", file=sys.stderr)

    if not (args.all or args.videos or args.posts or args.channels):
        print("\nNo output type specified. Use --all or specify --videos, --posts, and/or --channels", file=sys.stderr)
        print("Example: python3 extract_all_types.py watch-history.html --all", file=sys.stderr)


if __name__ == '__main__':
    main()
