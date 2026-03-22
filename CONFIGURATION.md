# Configuration Reference

All configurable options across every YTArchive component.

---

## Backend (`backend/`)

Configuration is loaded from a `.env` file in the `backend/` directory, or from actual environment variables. Environment variables take precedence over the `.env` file.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `../youtube_history.db` | Absolute or relative path to the SQLite database file. Relative paths are resolved from `backend/`. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed CORS origins. The React dev server and Safari extension origin must be included. |

### Example `.env`

```env
# backend/.env

# Path to the SQLite database
DB_PATH=/home/user/ytarchive/youtube_history.db

# Allow the React dev server and Safari extension
CORS_ORIGINS=http://localhost:3000,safari-web-extension://
```

### CORS

The backend's CORS middleware reads `CORS_ORIGINS` at startup. If you access the API from additional origins (e.g. a Tailscale IP, a different port, or the Safari extension running in another profile), add them to this variable:

```env
CORS_ORIGINS=http://localhost:3000,http://100.64.0.1:3000,safari-web-extension://
```

### Server Port

The port is not set via `.env`. Pass it to `uvicorn` at startup:

```bash
uvicorn main:app --port 8000        # default
uvicorn main:app --port 9000        # custom port
```

### Database Path Resolution

`DB_PATH` defaults to one directory above `backend/`, which puts the database at the project root. To store it elsewhere:

```env
DB_PATH=/data/ytarchive/youtube_history.db
```

The database is created automatically if it does not exist. Tables are created on first startup via migrations in `database.py`.

---

## Frontend (`frontend/`)

### Development Server

Edit `frontend/vite.config.js` to change the dev server port or the API proxy target.

```js
// frontend/vite.config.js
export default defineConfig({
  server: {
    port: 3000,                          // dev server port
    proxy: {
      '/api': 'http://localhost:8000',   // backend address
    },
  },
  build: {
    outDir: '../backend/static',         // production build output
    emptyOutDir: true,
  },
})
```

| Option | Default | Description |
|--------|---------|-------------|
| `server.port` | `3000` | Port for `npm run dev` |
| `server.proxy['/api']` | `http://localhost:8000` | Backend URL during development. All `/api/*` requests are forwarded here. |
| `build.outDir` | `../backend/static` | Output directory for `npm run build`. The backend serves files from this path in production. |

### Production API URL

In production (single-process mode), the React app is served by the FastAPI backend and calls `/api/*` relative to its own origin — no proxy or environment variable needed.

If you serve the frontend from a different origin than the backend, set `VITE_API_BASE_URL` in a `.env.production` file:

```env
# frontend/.env.production
VITE_API_BASE_URL=http://100.64.0.1:8000
```

Then update `frontend/src/api.js` to read it:

```js
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';
```

---

## Safari Extension (`safari-extension/`)

### `config.js`

The only configurable file in the extension. Edit before building/enabling.

```js
// safari-extension/config.js
const CONFIG = {
  API_BASE_URL: 'http://localhost:8000'
};
```

| Key | Default | Description |
|-----|---------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | Base URL of the FastAPI backend. Change to your Tailscale IP for remote access. Do **not** include a trailing slash. |

**Examples:**

```js
// Local only (default)
API_BASE_URL: 'http://localhost:8000'

// Tailscale remote access
API_BASE_URL: 'http://100.64.0.2:8000'

// Custom port
API_BASE_URL: 'http://localhost:9000'
```

After editing `config.js`, reload the extension: Safari → Settings → Extensions → toggle YTArchive off, then on.

### `manifest.json`

Defines extension metadata, permissions, and which pages content scripts run on.

```json
{
  "manifest_version": 3,
  "name": "YTArchive",
  "version": "1.0",
  "permissions": ["activeTab", "tabs", "storage"],
  "host_permissions": ["*://www.youtube.com/*"],
  "content_scripts": [
    {
      "matches": ["*://www.youtube.com/watch*"]
    }
  ]
}
```

| Field | Value | Notes |
|-------|-------|-------|
| `host_permissions` | `*://www.youtube.com/*` | Required to inject the content script and read page data. Do not remove. |
| `permissions.storage` | — | Used for the offline queue (`chrome.storage.local`). |
| `permissions.tabs` | — | Required for badge updates and SPA navigation detection. |
| `content_scripts[0].matches` | `*://www.youtube.com/watch*` | Limits content script injection to video pages only. |

To change the match pattern (e.g. to also run on shorts), edit `manifest.json`, then re-run `xcrun safari-web-extension-converter` and rebuild in Xcode.

---

## MCP Server (`mcp-server/`)

### `server.py` constants

Two constants at the top of `mcp-server/server.py`:

```python
BASE_URL = "http://localhost:8000/api"   # FastAPI backend
TIMEOUT  = 15                            # seconds per request
```

| Constant | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:8000/api` | Full base URL of the backend API, including `/api`. |
| `TIMEOUT` | `15` | Per-request HTTP timeout in seconds. Increase if your backend is slow or the database is large. |

These are source-level constants; edit the file to change them.

### Claude Code registration

The MCP server is registered in `.claude/settings.json`. This file is tracked in git so it applies to anyone cloning the repo with Claude Code.

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

| Field | Description |
|-------|-------------|
| `command` | Absolute path to the Python interpreter in the MCP server's virtual environment. |
| `args[0]` | Absolute path to `server.py`. |

Update both paths to match your actual clone location.

---

## Scripts (`scripts/`)

Scripts read configuration from command-line arguments, not environment variables.

### Common flags

All database-touching scripts accept `--db`:

```bash
python3 scripts/import_to_db.py cleaned.html --db /path/to/my.db
python3 scripts/query_db.py stats --db /path/to/my.db
python3 scripts/fetch_transcripts.py --db /path/to/my.db
```

If `--db` is omitted, scripts use the same default as the backend: `../youtube_history.db` relative to the script location (i.e. the project root).

### `clean_youtube_history.py`

```bash
python3 scripts/clean_youtube_history.py <input.html> [-o output.html]
```

| Flag | Description |
|------|-------------|
| `input.html` | Path to the raw Google Takeout `watch-history.html` |
| `-o`, `--output` | Output file path. Defaults to stdout if omitted. |

### `extract_all_types.py`

```bash
python3 scripts/extract_all_types.py <input.html> [--all] [--videos [file]] [--posts [file]] [--channels [file]]
```

| Flag | Default output name | Description |
|------|---------------------|-------------|
| `--all` | — | Extract all three types. Uses default output names. |
| `--videos [file]` | `<input>-videos.html` | Extract watched videos. |
| `--posts [file]` | `<input>-posts.html` | Extract community posts. |
| `--channels [file]` | `<input>-channels.html` | Extract channel statistics. |

### `import_to_db.py`

```bash
python3 scripts/import_to_db.py <input.html> [--db path]
```

| Flag | Default | Description |
|------|---------|-------------|
| `input.html` | — | Path to the cleaned HTML file (output of `clean_youtube_history.py` or `extract_all_types.py --videos`). |
| `--db` | `../youtube_history.db` | Path to the SQLite database. Created if it does not exist. |

### `query_db.py`

```bash
python3 scripts/query_db.py <command> [--db path]
```

| Command | Description |
|---------|-------------|
| `stats` | Total counts for videos, channels, posts |
| `top` | Top 20 channels by video count |
| `recent` | Videos watched in the last 7 days |
| `search <query>` | Search video titles |
| `channel <name>` | All watches for a specific channel |
| `export <file.csv>` | Export all videos to CSV |

### `fetch_transcripts.py`

```bash
python3 scripts/fetch_transcripts.py [--db path] [--limit N]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--db` | `../youtube_history.db` | Database path. |
| `--limit` | (all) | Maximum number of transcripts to fetch in this run. |

---

## Default Tag Colors

The backend seeds five default tags on first startup:

| Tag name | Hex color |
|----------|-----------|
| `reference` | `#3b82f6` |
| `to-rewatch` | `#f59e0b` |
| `to-download` | `#10b981` |
| `learning` | `#8b5cf6` |
| `favorite` | `#ef4444` |

Colors can be updated via `PATCH /api/tags/{id}` after startup. New tags created via the UI or API can use any valid hex color.

---

## Watchlist Statuses

The `watchlist.status` column is constrained to these values:

| Status | Description |
|--------|-------------|
| `to-rewatch` | Queued to watch again |
| `reference` | Keep for reference, not necessarily rewatching |
| `to-download` | Marked for local download |
| `in-progress` | Currently watching or partway through |
| `done` | Finished; no further action needed |

These are enforced by a `CHECK` constraint in the database and by the API's Pydantic models. The frontend Kanban board shows one column per status.
