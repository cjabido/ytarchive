# YTArchive MCP Server Design

## Goal

Expose the YTArchive YouTube history database to Claude Code AI agents via an MCP server, enabling automated workflows like adding watch history entries and auto-categorizing videos with tags.

## Architecture

**Location:** `mcp-server/server.py` (single file)
**Transport:** stdio (local use by Claude Code agents)
**Language:** Python + FastMCP
**Data access:** HTTP proxy to the existing FastAPI backend at `localhost:8000` via `httpx`
**No direct SQLite access** — all data operations go through the REST API to avoid schema drift and reuse existing validation logic.

The MCP server has no authentication, no API keys, and no LLM calls of its own. The calling Claude agent provides all reasoning; the server provides data access and write operations.

**Dependencies (`mcp-server/requirements.txt`):**
- `fastmcp`
- `httpx`

## Tools

### `ytarchive_add_watch_history`

Add a video watch entry to the database. Upserts the video record and appends a watch timestamp.

**Parameters:**
- `video_id` (string, required) — YouTube video ID (e.g. `dQw4w9WgXcQ`)
- `video_title` (string, required) — Video title
- `video_url` (string, required) — Full YouTube URL
- `channel_name` (string, optional) — Channel display name
- `channel_url` (string, optional) — Channel URL
- `watched_at` (string, optional) — ISO 8601 timestamp; defaults to now
- `fetch_transcript` (boolean, optional, default `false`) — Queue a background transcript fetch for this video. The transcript will not be available immediately; check `ytarchive_get_video_details` later to confirm it arrived.

**Returns:** Confirmation with video_id and watch timestamp applied.

**Calls:** `POST /api/videos`

---

### `ytarchive_list_videos`

Search and browse the video library with optional filters.

**Parameters:**
- `q` (string, optional) — Filter by video title (substring match)
- `channel` (string, optional) — Filter by channel name (substring match)
- `tag` (string, optional) — Filter by tag name (exact match)
- `sort` (string, optional, default `"last_watched"`) — Sort order: `"last_watched"`, `"watch_count"`, or `"title"`
- `page` (integer, optional, default 1) — Page number
- `per_page` (integer, optional, default 50, max 200) — Results per page

**Returns:** Paginated list of videos with id, title, channel, last watched date, watch count, and current tags. Response shape: `{total, page, per_page, videos: [{video_id, video_title, channel_name, last_watched, watch_count, tags}]}`.

**Calls:** `GET /api/videos`

---

### `ytarchive_list_tags`

Return all available tags with usage counts.

**Parameters:** None

**Returns:** List of `{id, name, color, video_count}` objects.

**Calls:** `GET /api/tags`

---

### `ytarchive_get_video_details`

Get full details for a specific video including watch history, applied tags, watchlist status, notes, and transcript (if available).

**Parameters:**
- `video_id` (string, required)

**Returns:** Full video detail object. The `transcript` field is either `null` (no transcript stored) or an object `{text: string, language: string|null, fetched_at: string}`. Agents should use `transcript.text` (truncated as needed) when making categorization decisions.

**Calls:** `GET /api/videos/{video_id}`

---

### `ytarchive_set_video_tags`

Replace the tag set on a video with a new list of tag IDs.

**Parameters:**
- `video_id` (string, required)
- `tag_ids` (list of integers, required) — IDs from `ytarchive_list_tags`; maximum 5. This limit is enforced by the MCP server (not the backend) and returns an error before calling the API if exceeded. It is intentional guidance to keep auto-categorization focused; agents that need to apply more tags must do so via the REST API directly.

**Returns:** Confirmation with the applied tag names.

**Calls:** `PUT /api/videos/{video_id}/tags`

---

## Agent Workflow: Auto-Categorization

The MCP server exposes primitives; the agent composes them. A typical auto-categorization workflow:

1. `ytarchive_get_video_details(video_id)` → get title, channel, transcript
2. `ytarchive_list_tags()` → get available tag names and IDs
3. Agent reasons: given the video context, which ≤5 tags are most appropriate?
4. `ytarchive_set_video_tags(video_id, [id1, id2, ...])` → apply the decision

No API key required — the calling Claude agent provides the reasoning.

## Configuration

**Setup (one-time):**

```bash
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add to `~/.claude/settings.json` (or project-level `.claude/settings.json`):

```json
{
  "mcpServers": {
    "ytarchive": {
      "command": "/path/to/youtube-history/mcp-server/.venv/bin/python",
      "args": ["/path/to/youtube-history/mcp-server/server.py"]
    }
  }
}
```

Use the absolute path to the venv's Python to avoid resolving to the system Python which won't have the required packages.

**Prerequisite:** The FastAPI backend must be running at `localhost:8000` before the MCP server is used. The MCP server does not auto-start the backend.

## Error Handling

- If the backend is unreachable, tools return a clear error message: `"Backend unavailable at localhost:8000 — ensure the FastAPI server is running."`
- If a video or tag is not found, the REST API's 404 is surfaced as a descriptive error string.
- The `set_video_tags` tool validates that `tag_ids` contains ≤5 items before calling the API and returns an error immediately if exceeded.
- Other non-2xx responses from the backend (e.g. 422 validation errors, 500s) are surfaced as: `"Backend error {status_code}: {detail}"` so the agent has enough context to diagnose and retry.

## File Structure

```
mcp-server/
  server.py          # FastMCP server — single file
  requirements.txt   # fastmcp, httpx
```

No new backend files. No changes to the existing FastAPI app.
