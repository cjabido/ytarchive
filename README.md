# YouTube Watch History Cleaner

Python scripts to clean up YouTube watch history exports from Google Takeout by removing CSS bloat and extracting semantic information.

## Scripts

1. **`clean_youtube_history.py`** - Simple script that extracts videos only
2. **`extract_all_types.py`** - Advanced script that separates videos, posts, and channels

## Problem

Google's YouTube watch history export includes a massive inline CSS blob (Material Design Lite) that makes the file:
- Extremely large (megabytes of CSS for simple history data)
- Hard to parse for AI/LLM tools
- Difficult to work with programmatically

## Solution

This script extracts only the semantic information:
- Video title and URL
- Channel name and URL
- Watch timestamp

The output is clean, readable HTML with minimal styling.

## Usage

### Script 1: clean_youtube_history.py (Simple - Videos Only)

Extract just the watched videos:

```bash
# Output to file
python3 clean_youtube_history.py watch-history.html -o cleaned-history.html

# Output to stdout
python3 clean_youtube_history.py watch-history.html

# View help
python3 clean_youtube_history.py --help
```

### Script 2: extract_all_types.py (Advanced - Separate by Type)

Extract videos, community posts, and channel statistics into separate files:

```bash
# Extract all types (videos, posts, channels)
python3 extract_all_types.py watch-history.html --all

# Extract only specific types
python3 extract_all_types.py watch-history.html --videos
python3 extract_all_types.py watch-history.html --posts
python3 extract_all_types.py watch-history.html --channels

# Custom output file names
python3 extract_all_types.py watch-history.html --videos my-videos.html --posts my-posts.html

# View help
python3 extract_all_types.py --help
```

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library)

## Examples

### Example 1: Simple Cleaning (Videos Only)

**Input:** 66MB HTML file with embedded CSS
**Output:** 26MB clean HTML (60% reduction)
**Result:** Single file with 66,076 video entries

### Example 2: Full Extraction (All Types)

**Input:** 66MB HTML file (watch-history.html)
**Output:**
- `watch-history-videos.html` (26MB) - 66,076 videos
- `watch-history-posts.html` (402KB) - 612 community posts
- `watch-history-channels.html` (5.4MB) - 13,878 unique channels with stats

**Before:**
```html
<style>/* 500KB of minified CSS */</style>
<div class="mdl-grid"><div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">
  <div class="mdl-grid"><div class="header-cell mdl-cell mdl-cell--12-col">
    <p class="mdl-typography--title">YouTube<br></p></div>
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Watched <a href="...">Video Title</a><br>
      <a href="...">Channel Name</a><br>
      Jan 10, 2026, 12:28:55 AM EST<br>
    </div>
    ...
```

**After:**
```html
<div class="video-entry">
  <div class="video-title">
    <a href="https://www.youtube.com/watch?v=...">Video Title</a>
  </div>
  <div class="channel-name">
    Channel: <a href="https://www.youtube.com/channel/...">Channel Name</a>
  </div>
  <div class="timestamp">
    Jan 10, 2026, 12:28:55 AM EST
  </div>
</div>
```

## Features

### clean_youtube_history.py
- Removes all Material Design Lite CSS bloat
- Strips unnecessary div classes and styling
- Preserves all semantic information (video title, channel, timestamp)
- Simple single-file output

### extract_all_types.py (All features above, plus:)
- Separates videos, posts, and channels into distinct files
- **Videos**: All watched videos with titles, channels, and timestamps
- **Posts**: Community posts viewed with titles, channels, and timestamps
- **Channels**: Comprehensive channel statistics including:
  - Total number of interactions (videos watched + posts viewed from that channel)
  - First and last interaction timestamps
  - Sorted by interaction count (most watched channels first)
- Handles both `/channel/` and `/@username` URL formats
- Properly escapes HTML entities
- Works with files of any size (tested with 66K+ video entries)

## How It Works

### clean_youtube_history.py
1. Uses regex to extract video entry blocks from the HTML
2. Parses each entry to extract:
   - Video URL and title
   - Channel URL and name
   - Timestamp
3. Generates clean HTML with minimal CSS for readability
4. Outputs to file or stdout

### extract_all_types.py
1. Uses regex to extract all entry blocks from the HTML
2. Identifies entry type by action verb:
   - "Watched" → Video entry
   - "Viewed" → Post entry
3. Extracts all channel references throughout the file
4. Aggregates channel statistics (count, first/last seen)
5. Generates three separate HTML files:
   - Videos with all metadata
   - Posts with all metadata
   - Channels sorted by interaction frequency

## Notes

- Some older entries may not have channel information (deleted/private videos)
- The script handles non-breaking spaces and other HTML entities correctly
- Progress information is printed to stderr, so you can redirect stdout separately
