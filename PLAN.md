# YTArchive — Project Plan

## Overview

A personal YouTube watch history management system with three components:

1. **FastAPI backend** — REST API over the existing SQLite database
2. **React frontend** — Web UI for browsing, tagging, and managing videos
3. **Safari extension** — Browser-side capture, tagging toast, and transcript fetch

The system extends the existing `youtube_history.db` (194k+ videos, 24k channels) rather than replacing it. All existing scripts (`query_db.py`, `fetch_transcripts.py`, etc.) remain usable independently.

---

## Key Decisions (already made)

| Decision | Choice | Reason |
|---|---|---|
| Backend language | Python + FastAPI | Consistent with existing scripts |
| Database | SQLite (extended) | Already populated, no migration needed |
| Hosting | Local (Mac) | Privacy, no cost, fast |
| Multi-device access | Tailscale | Already in use; exposes localhost over VPN |
| DB sync | Not synced — server is single source of truth | SQLite + iCloud = file locking issues |
| Build order | Backend → Frontend → Safari Extension | API must exist before clients |

---

## Architecture

```
┌─────────────────────────────────────┐
│           User Devices              │
│  Mac (localhost) / other via Tailscale│
│                                     │
│  ┌──────────────┐  ┌─────────────┐  │
│  │   React SPA  │  │   Safari    │  │
│  │  (port 3000) │  │  Extension  │  │
│  └──────┬───────┘  └──────┬──────┘  │
└─────────┼─────────────────┼─────────┘
          │ HTTP             │ HTTP
          ▼                  ▼
┌─────────────────────────────────────┐
│     FastAPI Backend (port 8000)     │
│     Serves API + static frontend    │
├─────────────────────────────────────┤
│         SQLite Database             │
│       youtube_history.db            │
│   (videos, channels, posts,         │
│    transcripts, tags, watchlist)    │
└─────────────────────────────────────┘
```

- The FastAPI server can serve the built React app as static files (single process)
- In dev mode, React runs on 3000 with CORS to FastAPI on 8000
- Safari extension talks to `http://localhost:8000` — no auth needed for local use
- For Tailscale access, expose the FastAPI port via Tailscale (no extra setup needed)

---

## Repository Structure

```
ytarchive/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── database.py           # SQLite connection, table setup
│   ├── models.py             # Pydantic models / schemas
│   ├── routers/
│   │   ├── videos.py         # /videos endpoints
│   │   ├── tags.py           # /tags endpoints
│   │   ├── watchlist.py      # /watchlist endpoints
│   │   ├── transcripts.py    # /transcripts endpoints
│   │   └── stats.py          # /stats endpoint
│   ├── services/
│   │   └── transcripts.py    # Transcript fetch logic (from existing script)
│   ├── requirements.txt
│   └── .env.example          # DB_PATH, CORS_ORIGINS
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Library.jsx   # Main browse/search view
│   │   │   ├── Watchlist.jsx # Watchlist management
│   │   │   └── Stats.jsx     # Analytics view
│   │   ├── components/
│   │   │   ├── VideoCard.jsx
│   │   │   ├── TagBadge.jsx
│   │   │   ├── TagPicker.jsx
│   │   │   └── TranscriptPane.jsx
│   │   └── api.js            # API client (fetch wrappers)
│   ├── package.json
│   └── vite.config.js
│
├── safari-extension/
│   ├── manifest.json         # WebExtension manifest v3
│   ├── background.js         # Service worker
│   ├── content.js            # YouTube page detector
│   ├── popup/
│   │   ├── popup.html        # Toast/popover UI
│   │   ├── popup.js
│   │   └── popup.css
│   └── icons/
│
├── scripts/                  # Existing scripts (moved here)
│   ├── clean_youtube_history.py
│   ├── extract_all_types.py
│   ├── fetch_transcripts.py
│   ├── import_to_db.py
│   └── query_db.py
│
├── youtube_history.db        # Symlink or path configured via .env
├── README.md
└── PLAN.md
```

---

## Phase 1 — Backend API

**Goal:** A running FastAPI server that wraps the existing DB with full CRUD for videos, tags, watchlist, and transcripts.

### Tasks
- [ ] Set up FastAPI project, `requirements.txt`, `.env` for DB path
- [ ] `database.py` — connection pool, run schema migrations (add new tables)
- [ ] Port transcript fetch logic from `fetch_transcripts.py` into `services/transcripts.py`
- [ ] Implement routers (see API.md for full spec)
- [ ] CORS config for localhost:3000 and Safari extension origin
- [ ] `GET /` serves React build (static files) in production mode
- [ ] Test all endpoints with curl / httpie

### Run command
```bash
cd backend
python3 -m uvicorn main:app --reload --port 8000
```

---

## Phase 2 — React Frontend

**Goal:** A usable web UI for browsing 194k videos, tagging, and managing the watchlist.

### Pages

**Library (main view)**
- Search bar (title, channel)
- Filter by tag, channel, date range
- Infinite scroll or paginated video cards
- Click video → slide-in detail panel with transcript, tags, watchlist controls

**Watchlist**
- Kanban or table view by status: `to-rewatch`, `reference`, `to-download`, `done`
- Drag to change status, click to open detail

**Stats**
- Top channels, viewing patterns by hour/day, tag distribution

### Stack
- Vite + React
- TailwindCSS
- React Query (data fetching + caching — important for 194k rows)
- shadcn/ui components

### Notes
- Always paginate — never fetch all 194k at once
- React Query handles optimistic updates well for tag changes
- In production, `vite build` output goes into `backend/static/` and FastAPI serves it

---

## Phase 3 — Safari Extension

**Goal:** Capture videos directly from YouTube, tag them inline, fetch transcripts — no Takeout needed.

### Behavior on `youtube.com/watch?v=*`

1. Extension icon activates (badge lights up)
2. Click icon → popover opens with:
   - Video title + channel (parsed from page DOM or YouTube API)
   - Tag picker (loads tags from API)
   - Status selector (watchlist status)
   - Optional notes field
   - "Save" button → POST `/videos` + POST `/video_tags`
   - "Fetch Transcript" button → POST `/transcripts/{id}/fetch`
3. Toast confirmation on save

### Key implementation notes
- Use `manifest_version: 3` (required for Safari 16+)
- Content script reads `document.title` and `window.location` for video ID and title
- Channel name from `ytInitialData` JSON in the page (injected by YouTube)
- API base URL configurable via extension options page (default: `http://localhost:8000`)
- Safari requires the extension to be wrapped in an Xcode project for signing — the WebExtension code itself is standard JS

### Xcode wrapping
```bash
xcrun safari-web-extension-converter safari-extension/ \
  --project-location . \
  --app-name YTArchive
```
This generates an Xcode project. Build once, enable in Safari → Preferences → Extensions. Re-run converter only if manifest changes.

---

## Phase 4 — YouTube API Integration (future)

- OAuth 2.0 with YouTube Data API v3
- Sync playlists to/from watchlist
- Add videos to YouTube playlists directly from the frontend
- Requires a Google Cloud project + OAuth consent screen

---

## Environment Variables

```env
# backend/.env
DB_PATH=/absolute/path/to/youtube_history.db
CORS_ORIGINS=http://localhost:3000,safari-web-extension://
PORT=8000
```

---

## Starting Point for Claude Code

1. `cd ~/Projects && mkdir ytarchive && cd ytarchive`
2. Copy/symlink `youtube_history.db` or set `DB_PATH` in `.env`
3. Move existing scripts into `scripts/`
4. Begin with `backend/` — see API.md for full endpoint spec
5. Reference `SCHEMA.md` for the DB changes needed
