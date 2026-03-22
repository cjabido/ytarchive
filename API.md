# YTArchive — API Specification

Base URL: `http://localhost:8000/api`

All responses are JSON. Errors follow: `{ "detail": "message" }`.

---

## Videos

### `GET /videos`
Browse and search the watch history. Always paginated.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `q` | string | — | Search video title |
| `channel` | string | — | Filter by channel name (partial match) |
| `tag` | string | — | Filter by tag name |
| `watchlist_status` | string | — | Filter by watchlist status |
| `has_transcript` | bool | — | Only videos with/without transcripts |
| `rewatched` | bool | — | Only videos watched more than once |
| `from_date` | ISO date | — | Filter watches on/after this date |
| `to_date` | ISO date | — | Filter watches on/before this date |
| `sort` | string | `last_watched` | `last_watched`, `watch_count`, `title` |
| `page` | int | 1 | Page number |
| `per_page` | int | 50 | Results per page (max 200) |

**Response:**
```json
{
  "total": 194338,
  "page": 1,
  "per_page": 50,
  "videos": [
    {
      "video_id": "dQw4w9WgXcQ",
      "video_title": "...",
      "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
      "channel_name": "...",
      "channel_url": "...",
      "last_watched": "2026-03-09T23:26:14",
      "watch_count": 3,
      "watchlist_status": "reference",
      "tags": ["reference", "learning"],
      "has_transcript": true
    }
  ]
}
```

---

### `GET /videos/{video_id}`
Get full detail for a single video.

**Response:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "video_title": "...",
  "video_url": "...",
  "channel_name": "...",
  "channel_url": "...",
  "watch_history": [
    { "watched_at": "2026-01-01T10:00:00" },
    { "watched_at": "2026-03-09T23:26:14" }
  ],
  "watch_count": 2,
  "tags": [
    { "id": 1, "name": "reference", "color": "#3b82f6" }
  ],
  "watchlist": {
    "status": "reference",
    "notes": "Great explanation of katakana ン vs ソ",
    "priority": 2,
    "added_at": "2026-03-10T08:00:00"
  },
  "notes": "...",
  "transcript": {
    "text": "...",
    "language": "en",
    "fetched_at": "2026-03-10T09:00:00"
  }
}
```

---

### `POST /videos`
Add a video directly (used by Safari extension — bypasses Takeout).

**Body:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "video_title": "Video Title",
  "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "channel_name": "Channel Name",
  "channel_url": "https://youtube.com/@channel",
  "watched_at": "2026-03-21T14:30:00",
  "tags": ["reference"],
  "watchlist_status": "reference",
  "notes": "optional note",
  "fetch_transcript": false
}
```

**Response:** `201 Created` — returns the created video object (same as GET /videos/{id})

> If `video_id` + `watched_at` already exists, returns `200` with existing record (idempotent).
> If `fetch_transcript: true`, queues a background transcript fetch.

---

## Tags

### `GET /tags`
List all tags.

**Response:**
```json
[
  { "id": 1, "name": "reference", "color": "#3b82f6", "video_count": 142 },
  { "id": 2, "name": "to-rewatch", "color": "#f59e0b", "video_count": 38 }
]
```

---

### `POST /tags`
Create a new tag.

**Body:** `{ "name": "japanese", "color": "#f97316" }`
**Response:** `201 Created` — `{ "id": 6, "name": "japanese", "color": "#f97316" }`

---

### `PATCH /tags/{tag_id}`
Update a tag's name or color.

**Body:** `{ "name": "jp-learning", "color": "#f97316" }`
**Response:** Updated tag object.

---

### `DELETE /tags/{tag_id}`
Delete a tag (cascades to video_tags).

**Response:** `204 No Content`

---

### `PUT /videos/{video_id}/tags`
Set the complete tag list for a video (replaces existing tags).

**Body:** `{ "tag_ids": [1, 3, 6] }`
**Response:** `{ "video_id": "...", "tags": [...] }`

---

### `POST /videos/{video_id}/tags/{tag_id}`
Add a single tag to a video.

**Response:** `201 Created` or `200` if already tagged.

---

### `DELETE /videos/{video_id}/tags/{tag_id}`
Remove a single tag from a video.

**Response:** `204 No Content`

---

## Watchlist

### `GET /watchlist`
Get all watchlist items with video info.

**Query params:**
| Param | Type | Description |
|---|---|---|
| `status` | string | Filter by status |
| `sort` | string | `priority`, `added_at`, `title` |

**Response:**
```json
[
  {
    "video_id": "...",
    "status": "reference",
    "notes": "...",
    "priority": 2,
    "added_at": "...",
    "video_title": "...",
    "channel_name": "...",
    "video_url": "...",
    "tags": ["reference"]
  }
]
```

---

### `POST /watchlist`
Add a video to the watchlist.

**Body:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "status": "to-rewatch",
  "notes": "optional",
  "priority": 0
}
```
**Response:** `201 Created` — watchlist item. Returns `200` if already exists (updates status/notes).

---

### `PATCH /watchlist/{video_id}`
Update a watchlist item's status, notes, or priority.

**Body:** `{ "status": "done", "notes": "finished watching" }`
**Response:** Updated watchlist item.

---

### `DELETE /watchlist/{video_id}`
Remove from watchlist.

**Response:** `204 No Content`

---

## Transcripts

### `GET /transcripts/{video_id}`
Get stored transcript for a video.

**Response:**
```json
{
  "video_id": "...",
  "transcript": "full text...",
  "language": "en",
  "fetched_at": "2026-03-10T09:00:00"
}
```
Returns `404` if no transcript stored.

---

### `POST /transcripts/{video_id}/fetch`
Trigger a transcript fetch for a video (runs in background).

**Response:** `202 Accepted`
```json
{ "status": "fetching", "video_id": "..." }
```

Poll `GET /transcripts/{video_id}` to check when it's ready.
Returns `200` immediately if transcript already exists.

---

### `GET /transcripts/{video_id}/obsidian`
Export transcript as Obsidian-formatted markdown.

**Response:** `text/markdown`
```markdown
---
title: "Video Title"
channel: "Channel Name"
url: https://youtube.com/watch?v=...
watched: 2026-03-09
tags: [youtube, reference]
---

# Video Title

**Channel:** Channel Name
**URL:** https://youtube.com/watch?v=...

## Transcript

Full transcript text here...
```

---

## Notes

### `GET /videos/{video_id}/notes`
Get personal notes for a video.

**Response:** `{ "video_id": "...", "content": "...", "updated_at": "..." }`

---

### `PUT /videos/{video_id}/notes`
Create or replace notes for a video.

**Body:** `{ "content": "My notes about this video..." }`
**Response:** Updated notes object.

---

## Stats

### `GET /stats`
Overall database stats.

**Response:**
```json
{
  "total_videos": 194338,
  "unique_videos": 162000,
  "total_channels": 24713,
  "total_tags": 6,
  "watchlist_count": 87,
  "transcript_count": 12,
  "rewatched_count": 4200,
  "top_channels": [
    { "channel_name": "...", "watch_count": 1240 }
  ],
  "watchlist_by_status": {
    "reference": 32,
    "to-rewatch": 28,
    "to-download": 15,
    "done": 12
  },
  "watches_by_hour": {
    "0": 120, "1": 80, ...
  }
}
```

---

## Safari Extension Endpoints Summary

The extension only needs these three calls:

1. `POST /videos` — save the current video with optional tags + watchlist status
2. `POST /transcripts/{video_id}/fetch` — trigger transcript fetch
3. `GET /tags` — populate the tag picker in the toast UI

---

## Notes for Implementation

- Use `aiosqlite` for async SQLite access with FastAPI
- All `watched_at` / `created_at` stored as ISO 8601 strings (SQLite has no native datetime)
- Video deduplication: when querying, `GROUP BY video_id` and use `MAX(watched_at)` as `last_watched`
- Transcript fetch is slow (network call) — run with `BackgroundTasks` in FastAPI
- Add `FTS5` virtual table on `videos.video_title` for fast full-text search if needed (SQLite supports this)
