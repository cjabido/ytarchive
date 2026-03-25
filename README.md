# YTArchive

A personal YouTube watch history management system. Import your Google Takeout export, browse and search 194k+ videos, tag and organize your watch history, capture new videos directly from Safari, and query everything with Claude Code agents.

## What's Included

| Component | Description |
|-----------|-------------|
| **Scripts** | Python utilities to clean Takeout exports and import them into SQLite |
| **Backend API** | FastAPI server exposing a REST API over your watch history database |
| **Web Interface** | React SPA for searching, tagging, watchlist management, and analytics |
| **Safari Extension** | Browser extension to capture videos and tag them without leaving YouTube |
| **MCP Server** | Model Context Protocol server exposing archive tools to Claude Code agents |

## Architecture

```
Safari Extension          React Web UI           Claude Code Agent
      │                       │                         │
      └───────────────────────┴─────────────────────────┘
                              │
                    FastAPI backend :8000
                     /api/videos
                     /api/tags
                     /api/watchlist
                     /api/transcripts
                     /api/stats
                              │
                    SQLite database
                    youtube_history.db
```

## Quick Start

### 1. Import your watch history

Get your YouTube history from [Google Takeout](https://takeout.google.com) (select "YouTube and YouTube Music" → "watch-history.html").

```bash
# Remove CSS bloat from the export
python3 scripts/clean_youtube_history.py watch-history.html -o cleaned.html

# Import into SQLite
python3 scripts/import_to_db.py cleaned.html
```

### 2. Start the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 3. Start the web interface (development)

```bash
cd frontend
npm install
npm run dev        # runs on http://localhost:3000
```

### 4. Or build for production (single process)

```bash
cd frontend
npm install
npm run build      # outputs to backend/static/

cd ../backend
uvicorn main:app --port 8000   # serves both API and UI
```

Open `http://localhost:8000` in your browser.

---

## Scripts

Six standalone Python utilities in `scripts/`. No backend required.

### `clean_youtube_history.py`

Strips the 500KB Material Design Lite CSS blob from a Takeout export, leaving clean readable HTML.

```bash
python3 scripts/clean_youtube_history.py watch-history.html -o cleaned.html
python3 scripts/clean_youtube_history.py watch-history.html   # stdout
python3 scripts/clean_youtube_history.py --help
```

**Input:** 66MB HTML with embedded CSS → **Output:** 26MB clean HTML (60% reduction)

### `extract_all_types.py`

Advanced extraction that separates videos, community posts, and channel statistics into distinct files.

```bash
# Extract everything
python3 scripts/extract_all_types.py watch-history.html --all

# Extract specific types
python3 scripts/extract_all_types.py watch-history.html --videos
python3 scripts/extract_all_types.py watch-history.html --posts
python3 scripts/extract_all_types.py watch-history.html --channels

# Custom output filenames
python3 scripts/extract_all_types.py watch-history.html \
  --videos my-videos.html \
  --posts my-posts.html

python3 scripts/extract_all_types.py --help
```

**Output files:**
- `watch-history-videos.html` — all watched videos with title, channel, timestamp
- `watch-history-posts.html` — community posts viewed
- `watch-history-channels.html` — unique channels sorted by interaction count

### `import_to_db.py`

Parses a cleaned HTML export and inserts records into SQLite. Idempotent — safe to run repeatedly with overlapping exports.

```bash
# Import using default DB path (youtube_history.db in project root)
python3 scripts/import_to_db.py cleaned.html

# Specify database path
python3 scripts/import_to_db.py cleaned.html --db /path/to/my.db

python3 scripts/import_to_db.py --help
```

Deduplicates on `(video_id, watched_at)`. Upserts channel records with `first_seen`/`last_seen` tracking.

### `query_db.py`

CLI for querying the database without writing SQL.

```bash
python3 scripts/query_db.py stats                    # database overview
python3 scripts/query_db.py top                      # top 20 channels
python3 scripts/query_db.py recent                   # last 7 days
python3 scripts/query_db.py search "machine learning" # title search
python3 scripts/query_db.py channel "3Blue1Brown"    # channel timeline
python3 scripts/query_db.py export output.csv        # CSV export

python3 scripts/query_db.py --help
```

### `import_ytdlp_history.py`

Alternative importer that reads a yt-dlp flat-playlist JSONL dump instead of Google Takeout HTML. Enriches entries with channel info via YouTube's oEmbed API (no API key required).

**Requires:** `aiohttp` (`pip install aiohttp`)

```bash
# First, dump your watch history with yt-dlp
yt-dlp --cookies-from-browser safari --flat-playlist --no-simulate \
    --playlist-end 200 --dump-json "https://www.youtube.com/feed/history" \
    > history.jsonl

# Import into the database
python3 scripts/import_ytdlp_history.py history.jsonl -d youtube_history.db

# Skip oEmbed enrichment (faster, but may lack channel info)
python3 scripts/import_ytdlp_history.py history.jsonl --no-enrich

python3 scripts/import_ytdlp_history.py --help
```

Uses async HTTP with 10 concurrent oEmbed requests. Deduplicates on `(video_id, watched_at)`.

### `fetch_transcripts.py`

Background script to bulk-fetch transcripts for videos already in the database.

**Requires:** `youtube-transcript-api` (`pip install youtube-transcript-api`)

```bash
# Fetch transcripts for all videos without one
python3 scripts/fetch_transcripts.py -d youtube_history.db fetch

# Limit to 50 videos, with 2s delay between requests
python3 scripts/fetch_transcripts.py fetch -n 50 --delay 2

# Search transcript content
python3 scripts/fetch_transcripts.py search "neural network"

# Export a single transcript to file
python3 scripts/fetch_transcripts.py export dQw4w9WgXcQ transcript.txt

# Show transcript coverage stats
python3 scripts/fetch_transcripts.py stats

python3 scripts/fetch_transcripts.py --help
```

Prefers manual captions over auto-generated. Stores transcripts with language codes. Includes built-in rate limiting to avoid YouTube bans.

> **Warning:** Don't fetch transcripts for large batches — YouTube may rate-limit or ban your IP.

---

## Web Interface

The React SPA runs at `http://localhost:3000` (dev) or `http://localhost:8000` (production).

### Pages

**Library** — Browse and search your entire watch history.
- Full-text search by title
- Filter by tag, channel, date range, or watchlist status
- Sort by last watched, watch count, or title
- Click any video to open a detail panel with full metadata, watch history, notes, and transcript

**Watchlist** — Kanban-style board organized by status.
- Statuses: `to-rewatch`, `reference`, `to-download`, `in-progress`, `done`
- Drag cards between columns to change status
- Set priority and add personal notes per video

**Stats** — Analytics dashboard.
- Top channels by watch count
- Viewing patterns by hour of day
- Tag distribution
- Watchlist status breakdown

### Tags

Tags are user-defined labels with custom hex colors. Five defaults are pre-loaded:

| Tag | Color |
|-----|-------|
| `reference` | Blue `#3b82f6` |
| `to-rewatch` | Amber `#f59e0b` |
| `to-download` | Green `#10b981` |
| `learning` | Purple `#8b5cf6` |
| `favorite` | Red `#ef4444` |

Create additional tags at any time. Tags apply to all watches of a video (not per-watch).

---

## Safari Extension

Capture and tag videos directly from YouTube without switching windows.

### What it does

- Shows a green badge on the extension icon when you're on a YouTube video page
- Opens a popup showing the current video's title, channel, and archive status
- Lets you add tags, set watchlist status, and write notes before saving
- Queues saves offline if the backend is unreachable and retries on next use

### Setup (one-time)

Prerequisites: Xcode installed, backend running.

```bash
# From the project root:
xcrun safari-web-extension-converter safari-extension/ \
  --project-location . \
  --app-name YTArchive \
  --macos-only
```

1. Open `YTArchive/YTArchive.xcodeproj` in Xcode
2. Press **Cmd+R** to build and run
3. In Safari: **Settings → Extensions → YTArchive** → enable
4. Click the extension icon on any YouTube page and grant permission for `youtube.com`

### Reloading after changes

- **JS / HTML / CSS changes:** Toggle the extension off then on in Safari Settings → Extensions
- **`manifest.json` or new files:** Re-run `xcrun safari-web-extension-converter` and rebuild in Xcode

### Remote access via Tailscale

To use the extension from another device on your Tailscale network, edit `safari-extension/config.js`:

```js
const CONFIG = {
  API_BASE_URL: 'http://100.x.x.x:8000'  // your Mac's Tailscale IP
};
```

Then toggle the extension off/on to pick up the change.

---

## MCP Server

Exposes YTArchive as tools for Claude Code agents via the Model Context Protocol (stdio transport).

### Available tools

| Tool | Description |
|------|-------------|
| `ytarchive_create_tag` | Create a new tag with name and color |
| `ytarchive_list_tags` | List all tags with video counts |
| `ytarchive_list_videos` | Search/filter videos with pagination |
| `ytarchive_get_video_details` | Full video record including transcript |
| `ytarchive_add_watch_history` | Add a video to the archive |
| `ytarchive_set_video_tags` | Replace tags on a video (max 5) |

### Setup

```bash
cd mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Register with Claude Code in `.claude/settings.json`:

```json
{
  "mcpServers": {
    "ytarchive": {
      "command": "/home/user/ytarchive/mcp-server/venv/bin/python",
      "args": ["/home/user/ytarchive/mcp-server/server.py"]
    }
  }
}
```

The MCP server requires the FastAPI backend to be running at `http://localhost:8000`.

### Example agent workflow

```
1. ytarchive_list_tags()              → get existing tag IDs
2. ytarchive_create_tag("tutorials")  → create a new tag if needed
3. ytarchive_list_videos(q="python")  → find untagged videos
4. ytarchive_get_video_details(id)    → read transcript for context
5. ytarchive_set_video_tags(id, [3])  → apply "learning" tag
```

---

## Database

Single SQLite file: `youtube_history.db` (default location: project root).

### Tables

| Table | Purpose |
|-------|---------|
| `videos` | Watch history — title, URL, channel, timestamps |
| `channels` | Channel metadata — name, URL, first/last seen |
| `posts` | Community posts viewed |
| `transcripts` | Cached video transcripts with language codes |
| `tags` | User-defined labels with hex colors |
| `video_tags` | Many-to-many: videos ↔ tags |
| `watchlist` | Per-video status, priority, and notes |
| `video_notes` | Long-form personal notes per video |

New tables (`tags`, `video_tags`, `watchlist`, `video_notes`, `transcripts`) are created automatically on first backend startup.

See [SCHEMA.md](SCHEMA.md) for full DDL and example queries.

---

## REST API

Full API reference at [API.md](API.md). Interactive docs at `http://localhost:8000/docs` when the backend is running.

**Base URL:** `http://localhost:8000/api`

| Prefix | Purpose |
|--------|---------|
| `/videos` | Search, detail, add, tag, notes |
| `/tags` | Create, list, update, delete tags |
| `/watchlist` | Manage watchlist status and notes |
| `/transcripts` | Fetch, retrieve, export as Obsidian Markdown |
| `/stats` | Aggregate analytics |

---

## Requirements

**Scripts:** Python 3.6+ (3.10+ for `import_ytdlp_history.py`). Some scripts have optional dependencies — install with `pip install -r scripts/requirements.txt`

**Backend:**
- Python 3.11+
- fastapi, uvicorn, aiosqlite, pydantic, python-dotenv, youtube-transcript-api

**Frontend:**
- Node.js 18+
- React 18, Vite, TailwindCSS 4, React Query 5

**Safari Extension:**
- macOS with Xcode installed
- Safari 14+

**MCP Server:**
- Python 3.11+
- fastmcp, httpx

---

## Further Reading

- [CONFIGURATION.md](CONFIGURATION.md) — all configuration options for every component
- [DEPLOYMENT.md](DEPLOYMENT.md) — single-machine, multi-device, and production deployment
- [API.md](API.md) — full REST API reference
- [SCHEMA.md](SCHEMA.md) — database schema and example queries
- [LONG_TERM_TRACKING.md](LONG_TERM_TRACKING.md) — scheduled imports and long-term maintenance
