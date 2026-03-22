# YTArchive — Database Schema

## Existing Tables (do not modify structure)

### `videos`
```sql
CREATE TABLE videos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL,
    video_url   TEXT NOT NULL,
    video_title TEXT NOT NULL,
    channel_id  TEXT,
    watched_at  TEXT NOT NULL,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    UNIQUE(video_id, watched_at)
);
```
> Note: `video_id` is not unique alone — the same video can appear multiple times
> if watched on different dates. Dedup on `video_id` when joining to tags/watchlist.

### `channels`
```sql
CREATE TABLE channels (
    channel_id   TEXT PRIMARY KEY,
    channel_name TEXT NOT NULL,
    channel_url  TEXT NOT NULL,
    first_seen   TEXT,
    last_seen    TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### `posts`
```sql
CREATE TABLE posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id    TEXT NOT NULL,
    post_url   TEXT NOT NULL,
    post_title TEXT NOT NULL,
    channel_id TEXT,
    viewed_at  TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    UNIQUE(post_id, viewed_at)
);
```

### `transcripts`
```sql
CREATE TABLE transcripts (
    video_id   TEXT PRIMARY KEY,
    transcript TEXT NOT NULL,
    language   TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);
```

---

## New Tables (add via migration on startup)

### `tags`
User-defined labels. Support color for UI rendering.

```sql
CREATE TABLE IF NOT EXISTS tags (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    color      TEXT NOT NULL DEFAULT '#6366f1',  -- hex color
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Seed data (insert if not exists):**
```sql
INSERT OR IGNORE INTO tags (name, color) VALUES
    ('reference',   '#3b82f6'),   -- blue
    ('to-rewatch',  '#f59e0b'),   -- amber
    ('to-download', '#10b981'),   -- green
    ('learning',    '#8b5cf6'),   -- purple
    ('favorite',    '#ef4444');   -- red
```

---

### `video_tags`
Many-to-many between a video (by `video_id`) and tags.
Uses `video_id` not `videos.id` so a tag applies to all watches of that video.

```sql
CREATE TABLE IF NOT EXISTS video_tags (
    video_id   TEXT NOT NULL,
    tag_id     INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (video_id, tag_id),
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
```

---

### `watchlist`
One row per video (by `video_id`). Tracks status and optional notes.

```sql
CREATE TABLE IF NOT EXISTS watchlist (
    video_id   TEXT PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'to-rewatch',
    notes      TEXT,
    priority   INTEGER NOT NULL DEFAULT 0,   -- higher = more important
    added_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('to-rewatch', 'reference', 'to-download', 'in-progress', 'done'))
);
```

---

### `video_notes`
Free-form personal notes per video (separate from watchlist notes, for richer content).

```sql
CREATE TABLE IF NOT EXISTS video_notes (
    video_id   TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## Migration Strategy

Run these in `database.py` on every startup using `CREATE TABLE IF NOT EXISTS`.
No external migration tool needed for SQLite at this scale.

```python
MIGRATIONS = [
    """CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        color TEXT NOT NULL DEFAULT '#6366f1',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",

    """INSERT OR IGNORE INTO tags (name, color) VALUES
        ('reference',   '#3b82f6'),
        ('to-rewatch',  '#f59e0b'),
        ('to-download', '#10b981'),
        ('learning',    '#8b5cf6'),
        ('favorite',    '#ef4444')""",

    """CREATE TABLE IF NOT EXISTS video_tags (
        video_id TEXT NOT NULL,
        tag_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (video_id, tag_id),
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
    )""",

    """CREATE TABLE IF NOT EXISTS watchlist (
        video_id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'to-rewatch',
        notes TEXT,
        priority INTEGER NOT NULL DEFAULT 0,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        CHECK (status IN ('to-rewatch', 'reference', 'to-download', 'in-progress', 'done'))
    )""",

    """CREATE TABLE IF NOT EXISTS video_notes (
        video_id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
]
```

---

## Useful Queries

### Get a video with all its tags and watchlist status
```sql
SELECT
    v.video_id,
    v.video_title,
    v.video_url,
    c.channel_name,
    MAX(v.watched_at) as last_watched,
    COUNT(DISTINCT v.id) as watch_count,
    w.status as watchlist_status,
    GROUP_CONCAT(t.name, ',') as tags
FROM videos v
LEFT JOIN channels c ON v.channel_id = c.channel_id
LEFT JOIN watchlist w ON v.video_id = w.video_id
LEFT JOIN video_tags vt ON v.video_id = vt.video_id
LEFT JOIN tags t ON vt.tag_id = t.id
WHERE v.video_id = ?
GROUP BY v.video_id;
```

### Search videos by title with tag filter
```sql
SELECT
    v.video_id,
    v.video_title,
    v.video_url,
    c.channel_name,
    MAX(v.watched_at) as last_watched,
    COUNT(DISTINCT v.id) as watch_count,
    w.status as watchlist_status,
    GROUP_CONCAT(DISTINCT t.name) as tags
FROM videos v
LEFT JOIN channels c ON v.channel_id = c.channel_id
LEFT JOIN watchlist w ON v.video_id = w.video_id
LEFT JOIN video_tags vt ON v.video_id = vt.video_id
LEFT JOIN tags t ON vt.tag_id = t.id
WHERE v.video_title LIKE ?
GROUP BY v.video_id
ORDER BY last_watched DESC
LIMIT ? OFFSET ?;
```

### Most rewatched videos (video_id appears multiple times)
```sql
SELECT
    v.video_id,
    v.video_title,
    c.channel_name,
    COUNT(*) as watch_count,
    MIN(v.watched_at) as first_watched,
    MAX(v.watched_at) as last_watched
FROM videos v
LEFT JOIN channels c ON v.channel_id = c.channel_id
GROUP BY v.video_id
HAVING watch_count > 1
ORDER BY watch_count DESC
LIMIT 50;
```

### Watchlist with full video info
```sql
SELECT
    w.video_id,
    w.status,
    w.notes,
    w.priority,
    w.added_at,
    v.video_title,
    v.video_url,
    c.channel_name,
    GROUP_CONCAT(DISTINCT t.name) as tags
FROM watchlist w
JOIN videos v ON w.video_id = v.video_id
LEFT JOIN channels c ON v.channel_id = c.channel_id
LEFT JOIN video_tags vt ON w.video_id = vt.video_id
LEFT JOIN tags t ON vt.tag_id = t.id
GROUP BY w.video_id
ORDER BY w.priority DESC, w.added_at DESC;
```
