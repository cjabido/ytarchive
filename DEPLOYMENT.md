# Deployment Guide

Instructions for every deployment scenario: local development, Docker Compose, single-machine production, and multi-device access over Tailscale.

---

## Prerequisites

| Tool | Minimum version | Purpose |
|------|----------------|---------|
| Python | 3.11+ | Backend and scripts |
| Node.js | 18+ | Frontend build (local dev only) |
| npm | 9+ | Frontend dependencies (local dev only) |
| Docker | 24+ | Docker Compose deployment |
| Docker Compose | 2.20+ | Docker Compose deployment |
| Xcode | Latest | Safari extension build (macOS only) |
| Git | Any | Clone the repo |

---

## 1. First-Time Setup

### Clone the repo

```bash
git clone <repo-url> ytarchive
cd ytarchive
```

### Import your watch history (optional but recommended before starting the backend)

```bash
# Clean your Google Takeout export
python3 scripts/clean_youtube_history.py watch-history.html -o cleaned.html

# Import into SQLite (creates youtube_history.db in the project root)
python3 scripts/import_to_db.py cleaned.html
```

---

## 2. Docker Compose (Recommended)

The fastest way to get everything running. Docker builds the frontend, starts the API, and serves the web interface — no local Python or Node installation required.

### Start all services

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Web interface | `http://localhost:3000` |
| API + Swagger docs | `http://localhost:8000/docs` |

### Stop

```bash
docker compose down
```

### Configuration

Copy `.env.example` to `.env` and edit as needed before starting:

```bash
cp .env.example .env
```

```env
# Port the API is exposed on (default: 8000)
API_PORT=8000

# Port the frontend is exposed on (default: 3000)
FRONTEND_PORT=3000

# CORS origins allowed by the backend
CORS_ORIGINS=http://localhost:3000,http://localhost,safari-web-extension://
```

### Database persistence

The SQLite database is stored in a Docker named volume (`db-data`) and persists across `docker compose down` / `up` cycles. To see where Docker stores it:

```bash
docker volume inspect ytarchive_db-data
```

### Importing watch history into the Docker database

The import scripts run against a local file path. The simplest approach is to run the scripts before starting Docker (they create `youtube_history.db` in the project root), then copy the file into the volume on first start.

Alternatively, copy an existing database into the running container:

```bash
# Copy a local database file into the named volume
docker compose cp youtube_history.db api:/data/youtube_history.db
```

Or run the import scripts directly inside the container:

```bash
# Copy your cleaned export into the container then run the import
docker compose cp cleaned.html api:/tmp/cleaned.html
docker compose exec api python3 -c "
import sys; sys.path.insert(0, '/app')
"
# The import scripts live in /scripts — run from outside the container
# against the volume-mounted database path is easier:
docker run --rm \
  -v ytarchive_db-data:/data \
  -v "$(pwd)/scripts":/scripts \
  -v "$(pwd)/cleaned.html":/tmp/cleaned.html \
  python:3.11-slim \
  python /scripts/import_to_db.py /tmp/cleaned.html --db /data/youtube_history.db
```

### MCP Server with Docker (optional)

The MCP server communicates over stdio and is not started by default. To run it interactively:

```bash
docker compose run --rm mcp
```

For Claude Code integration, it is simpler to run the MCP server directly (see [section 7](#7-mcp-server)) rather than through Docker, since Claude Code manages the subprocess itself.

### Rebuild after code changes

```bash
docker compose up --build
```

Only changed layers are rebuilt — subsequent builds are fast.

---

## 3. Local Development

Run backend and frontend as separate processes. The Vite dev server proxies API calls to the backend.

### Backend

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) configure via .env
cp .env.example .env              # edit DB_PATH, CORS_ORIGINS if needed

# Start with hot reload
uvicorn main:app --reload --port 8000
```

The backend runs at `http://localhost:8000`.
Interactive API docs: `http://localhost:8000/docs`

### Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The web interface is at `http://localhost:3000`. API calls are proxied to `http://localhost:8000`.

### MCP Server (optional)

In a third terminal:

```bash
cd mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 server.py
```

Or let Claude Code manage the process via `.claude/settings.json` (see [CONFIGURATION.md](CONFIGURATION.md)).

### Safari Extension (optional)

See section 6 below.

---

## 4. Single-Machine Production

Build the frontend once and serve everything from a single FastAPI process.

### Build the frontend

```bash
cd frontend
npm install
npm run build
# Outputs to backend/static/
```

### Start the backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

FastAPI serves the React app from `backend/static/` at `/` and the API at `/api/*`. Open `http://localhost:8000`.

### Keep it running with a process manager

**Using `nohup` (simple):**

```bash
cd backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > ../ytarchive.log 2>&1 &
echo $! > ../ytarchive.pid

# Stop later:
kill $(cat ../ytarchive.pid)
```

**Using `systemd` (macOS: use launchd instead):**

Create `/etc/systemd/system/ytarchive.service`:

```ini
[Unit]
Description=YTArchive backend
After=network.target

[Service]
User=youruser
WorkingDirectory=/home/youruser/ytarchive/backend
Environment=PATH=/home/youruser/ytarchive/backend/venv/bin
ExecStart=/home/youruser/ytarchive/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ytarchive
sudo systemctl start ytarchive
sudo systemctl status ytarchive
```

**Using `launchd` on macOS:**

Create `~/Library/LaunchAgents/com.ytarchive.backend.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.ytarchive.backend</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/youruser/ytarchive/backend/venv/bin/uvicorn</string>
    <string>main:app</string>
    <string>--host</string>
    <string>0.0.0.0</string>
    <string>--port</string>
    <string>8000</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/youruser/ytarchive/backend</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/youruser/ytarchive/ytarchive.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/youruser/ytarchive/ytarchive.err</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.ytarchive.backend.plist
launchctl start com.ytarchive.backend

# Stop:
launchctl stop com.ytarchive.backend
launchctl unload ~/Library/LaunchAgents/com.ytarchive.backend.plist
```

---

## 5. Multi-Device Access (Tailscale)

Access your archive from any device on your Tailscale network — iPhone, iPad, another Mac, etc.

### On the host machine

1. Install [Tailscale](https://tailscale.com) and sign in.
2. Note your machine's Tailscale IP (`tailscale ip -4`), e.g. `100.64.0.2`.
3. Start the backend bound to all interfaces:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

4. Update `CORS_ORIGINS` in `backend/.env` to include the Tailscale IP:

```env
CORS_ORIGINS=http://localhost:3000,http://100.64.0.2:8000
```

### With Docker Compose

Update your `.env` file in the project root:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost,http://100.64.0.2:3000,safari-web-extension://
```

Then restart:

```bash
docker compose up --build
```

Open `http://100.64.0.2:3000` on any device on your Tailscale network.

### On other devices (non-Docker)

Open `http://100.64.0.2:8000` in any browser on your Tailscale network.

### Safari Extension on another Mac

Edit `safari-extension/config.js` on the remote Mac before building:

```js
const CONFIG = {
  API_BASE_URL: 'http://100.64.0.2:8000'
};
```

Then rebuild the extension (see section 6).

---

## 6. Safari Extension

### Build and install (one-time)

Prerequisites:
- Xcode (latest from the App Store)
- Backend running at the address set in `safari-extension/config.js`

**Step 1 — Convert to Xcode project:**

```bash
# From the project root
xcrun safari-web-extension-converter safari-extension/ \
  --project-location . \
  --app-name YTArchive \
  --macos-only
```

This creates an `YTArchive/` directory with an Xcode project.

**Step 2 — Build and run in Xcode:**

```bash
open YTArchive/YTArchive.xcodeproj
```

Press **Cmd+R** to build and run. The app launches briefly and installs the extension.

**Step 3 — Enable in Safari:**

1. Safari → **Settings** → **Extensions**
2. Check **YTArchive**
3. Navigate to any YouTube video page
4. Click the extension icon → **Always Allow on youtube.com**

### Update the extension after code changes

**JS / HTML / CSS changes only:**
1. Edit the files in `safari-extension/`
2. Safari → Settings → Extensions → uncheck YTArchive, then re-check it

**`manifest.json` changes or new files added:**
1. Re-run `xcrun safari-web-extension-converter` (same command as above, overwrite when prompted)
2. Rebuild in Xcode (Cmd+R)

### Changing the backend URL

Edit `safari-extension/config.js`, then reload the extension (toggle off/on in Safari Settings).

---

## 7. MCP Server

### Setup

```bash
cd mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Register with Claude Code

Edit `.claude/settings.json` with the correct absolute paths for your machine:

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

Claude Code starts the MCP server automatically when it needs it. No separate process to manage.

### Verify the MCP server works

The MCP server requires the FastAPI backend to be running. Start the backend first, then in Claude Code:

```
> @ytarchive list all tags
```

If the backend is not running, you will see:
```
Backend unavailable at localhost:8000 — ensure the FastAPI server is running.
```

---

## 8. Scheduled Imports

To keep your archive up to date automatically, schedule periodic Takeout imports.

### Manual workflow (simplest)

1. Download a new Takeout export from [takeout.google.com](https://takeout.google.com)
2. Run the import script — it is idempotent and deduplicates automatically:

```bash
python3 scripts/clean_youtube_history.py new-export.html -o cleaned.html
python3 scripts/import_to_db.py cleaned.html
```

### Cron job (Linux/macOS)

```bash
crontab -e
```

Add a weekly job (runs every Sunday at 2am):

```cron
0 2 * * 0 /home/user/ytarchive/scripts/import_to_db.py /home/user/downloads/cleaned.html >> /home/user/ytarchive/import.log 2>&1
```

See [LONG_TERM_TRACKING.md](LONG_TERM_TRACKING.md) for a detailed guide including browser automation and backup strategies.

---

## 9. Database Backup

The entire archive is a single SQLite file. Back it up with any file copy.

```bash
# Simple copy
cp youtube_history.db youtube_history.backup.db

# Or use SQLite's built-in backup (safe while backend is running)
sqlite3 youtube_history.db ".backup '/path/to/backup.db'"

# Timestamped backup
sqlite3 youtube_history.db ".backup 'youtube_history_$(date +%Y%m%d).db'"
```

The WAL journal mode (`PRAGMA journal_mode=WAL`) makes hot backups safe — you can copy the database while the backend is running.

### Backing up the Docker volume

When running via Docker Compose, the database lives in the `ytarchive_db-data` named volume. Back it up by copying it out:

```bash
# Copy database from the volume to the current directory
docker compose cp api:/data/youtube_history.db ./youtube_history.backup.db

# Or with a timestamp
docker compose cp api:/data/youtube_history.db \
  "./youtube_history_$(date +%Y%m%d).db"
```

### What to back up

| File | Important? | Notes |
|------|-----------|-------|
| `youtube_history.db` | Yes | Your entire archive (or copy from Docker volume) |
| `backend/.env` | Yes | Configuration (local dev) |
| `.env` | Yes | Configuration (Docker Compose) |
| `safari-extension/config.js` | Yes if customized | API URL |
| `.claude/settings.json` | Yes | MCP registration |

---

## 10. Upgrading

### Pull latest code

```bash
git pull origin main
```

### Docker Compose upgrade

```bash
git pull origin main
docker compose up --build
```

Docker rebuilds only changed layers. The database volume is untouched.

### Update Python dependencies (local dev)

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade

cd ../mcp-server
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### Update Node dependencies (local dev)

```bash
cd frontend
npm install
npm run build   # rebuild if running in production mode
```

### Database migrations

The backend runs migrations automatically on startup. New tables and schema changes are applied with `CREATE TABLE IF NOT EXISTS` — your existing data is never dropped.

### Safari Extension

If extension files changed, rebuild:

```bash
xcrun safari-web-extension-converter safari-extension/ \
  --project-location . \
  --app-name YTArchive \
  --macos-only
# Open Xcode, Cmd+R
```

---

## 11. Troubleshooting

### Docker Compose issues

**Services won't start:**

```bash
# Check logs for all services
docker compose logs

# Check logs for a specific service
docker compose logs api
docker compose logs frontend
```

**Port already in use:**

Change the port in `.env`:

```env
API_PORT=8001
FRONTEND_PORT=3001
```

Then restart: `docker compose up`.

**Frontend can't reach the API:**

The frontend nginx config proxies `/api/` to the `api` service by name. If you see network errors in the browser console, confirm the `api` container is healthy:

```bash
docker compose ps
```

The `api` service uses a health check — `frontend` waits for it to pass before starting.

**Database is empty after restart:**

Confirm the volume exists and is mounted:

```bash
docker volume ls | grep ytarchive
docker compose exec api ls /data
```

If the volume was deleted, recreate it and re-import your data (see section 2).

**Rebuild a single service:**

```bash
docker compose up --build api
docker compose up --build frontend
```

### Backend won't start

```bash
# Check Python version
python3 --version  # must be 3.11+

# Verify dependencies
pip list | grep fastapi

# Check .env syntax
cat backend/.env

# Try verbose output
uvicorn main:app --reload --port 8000 --log-level debug
```

### Frontend shows no data / CORS errors

1. Confirm the backend is running: `curl http://localhost:8000/api/stats`
2. Check `CORS_ORIGINS` in `backend/.env` (local) or `.env` (Docker) includes your frontend origin
3. In dev mode, verify Vite proxy in `frontend/vite.config.js` points to the correct backend port

### Safari extension shows "Server unavailable"

1. Confirm the backend is running
2. Check `API_BASE_URL` in `safari-extension/config.js`
3. Toggle the extension off/on in Safari Settings to reload `config.js`
4. Check the browser console in the extension popup (right-click → Inspect Element)

### MCP server errors

```
Backend unavailable at localhost:8000
```
Start the FastAPI backend first.

```
Not found: /videos/dQw4w9WgXcQ
```
The video is not in your archive yet. Use `ytarchive_add_watch_history` to add it.

### Database locked

The WAL journal mode prevents most lock issues. If you see `database is locked`:
1. Close any other processes connected to the database
2. Check for zombie uvicorn processes: `ps aux | grep uvicorn`
3. Delete the WAL files if no process is running: `rm youtube_history.db-wal youtube_history.db-shm`

### Transcript fetch fails

The transcript API has rate limits. Symptoms: `TranscriptsDisabled` or `NoTranscriptFound` errors in the backend log.

- Not all videos have transcripts — this is normal
- Try again later for rate limit errors
- Some videos have transcripts in non-English languages only; the API tries English first then falls back to any available language
