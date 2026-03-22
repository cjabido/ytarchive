"""
YTArchive MCP Server

Exposes the YTArchive FastAPI backend as MCP tools for Claude Code agents.
Transport: stdio (local agents only).
All data operations proxy through http://localhost:8000.
"""

import httpx
from fastmcp import FastMCP

BASE_URL = "http://localhost:8000/api"
TIMEOUT = 15  # seconds for backend requests

mcp = FastMCP("ytarchive")


# ── HTTP helpers ──────────────────────────────────────────────────────────────

async def _raise_for_status(r: httpx.Response, path: str) -> None:
    """Raise RuntimeError with a descriptive message for non-2xx responses."""
    if r.status_code == 404:
        raise RuntimeError(f"Not found: {path}")
    if not r.is_success:
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise RuntimeError(f"Backend error {r.status_code}: {detail}")


async def _get(path: str, **params) -> dict:
    """GET request to the backend. Raises on non-2xx."""
    filtered = {k: v for k, v in params.items() if v is not None}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{BASE_URL}{path}", params=filtered)
    except httpx.ConnectError:
        raise RuntimeError(
            "Backend unavailable at localhost:8000 — ensure the FastAPI server is running."
        )
    await _raise_for_status(r, path)
    return r.json()


async def _post(path: str, body: dict) -> dict:
    """POST request to the backend."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{BASE_URL}{path}", json=body)
    except httpx.ConnectError:
        raise RuntimeError(
            "Backend unavailable at localhost:8000 — ensure the FastAPI server is running."
        )
    await _raise_for_status(r, path)
    return r.json()


async def _put(path: str, body: dict) -> dict:
    """PUT request to the backend."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.put(f"{BASE_URL}{path}", json=body)
    except httpx.ConnectError:
        raise RuntimeError(
            "Backend unavailable at localhost:8000 — ensure the FastAPI server is running."
        )
    await _raise_for_status(r, path)
    return r.json()


@mcp.tool
async def ytarchive_list_tags() -> str:
    """Return all available tags with usage counts.

    Returns a JSON list of {id, name, color, video_count} objects.
    Use the `id` values when calling ytarchive_set_video_tags.
    """
    try:
        tags = await _get("/tags")
        return str(tags)
    except RuntimeError as e:
        return str(e)


@mcp.tool
async def ytarchive_list_videos(
    q: str | None = None,
    channel: str | None = None,
    tag: str | None = None,
    sort: str | None = None,
    page: int | None = None,
    per_page: int | None = None,
) -> str:
    """Search and browse the video library.

    Args:
        q: Filter by video title (substring match).
        channel: Filter by channel name (substring match).
        tag: Filter by tag name (exact match).
        sort: Sort order — 'last_watched' (default), 'watch_count', or 'title'.
        page: Page number (default 1).
        per_page: Results per page (default 50, max 200).

    Returns JSON: {total, page, per_page, videos: [{video_id, video_title,
    channel_name, last_watched, watch_count, tags}]}
    """
    try:
        data = await _get(
            "/videos",
            q=q, channel=channel, tag=tag, sort=sort, page=page, per_page=per_page,
        )
        return str(data)
    except RuntimeError as e:
        return str(e)


@mcp.tool
async def ytarchive_get_video_details(video_id: str) -> str:
    """Get full details for a specific video.

    Args:
        video_id: YouTube video ID (e.g. 'dQw4w9WgXcQ').

    Returns the full video record including watch history, tags, watchlist status,
    notes, and transcript. The `transcript` field is null if no transcript is stored,
    otherwise {text, language, fetched_at}. Use transcript.text (truncated as needed)
    when making auto-categorization decisions.
    """
    try:
        data = await _get(f"/videos/{video_id}")
        return str(data)
    except RuntimeError as e:
        return str(e)


@mcp.tool
async def ytarchive_add_watch_history(
    video_id: str,
    video_title: str,
    video_url: str,
    channel_name: str | None = None,
    channel_url: str | None = None,
    watched_at: str | None = None,
    fetch_transcript: bool = False,
) -> str:
    """Add a video watch entry to the database.

    Upserts the video record and appends a watch timestamp. Safe to call multiple
    times for the same video — each call adds a new watch entry.

    Args:
        video_id: YouTube video ID (e.g. 'dQw4w9WgXcQ').
        video_title: Video title.
        video_url: Full YouTube URL.
        channel_name: Channel display name (optional).
        channel_url: Channel URL (optional).
        watched_at: ISO 8601 timestamp (optional, defaults to now).
        fetch_transcript: Queue a background transcript fetch (default False).
            Transcript will NOT be available immediately — check
            ytarchive_get_video_details later to confirm it arrived.

    Returns confirmation with video_id and watch timestamp.
    """
    body: dict = {
        "video_id": video_id,
        "video_title": video_title,
        "video_url": video_url,
        "fetch_transcript": fetch_transcript,
    }
    if channel_name is not None:
        body["channel_name"] = channel_name
    if channel_url is not None:
        body["channel_url"] = channel_url
    if watched_at is not None:
        body["watched_at"] = watched_at

    try:
        data = await _post("/videos", body)
        return f"Watch entry added. video_id={data.get('video_id')} watched_at={data.get('watched_at', 'recorded')}"
    except RuntimeError as e:
        return str(e)


@mcp.tool
async def ytarchive_set_video_tags(video_id: str, tag_ids: list[int]) -> str:
    """Replace the tag set on a video with a new list of tag IDs.

    Args:
        video_id: YouTube video ID.
        tag_ids: List of tag IDs from ytarchive_list_tags. Maximum 5.
            This limit is enforced here to keep auto-categorization focused.
            Call ytarchive_list_tags first to resolve tag names to IDs.

    Returns confirmation with the applied tag names.
    """
    if len(tag_ids) > 5:
        return f"Error: maximum 5 tags allowed (got {len(tag_ids)}). This limit keeps auto-categorization focused."

    try:
        data = await _put(f"/videos/{video_id}/tags", {"tag_ids": tag_ids})
        applied = [t["name"] for t in data.get("tags", [])]
        return f"Tags applied to {video_id}: {', '.join(applied) if applied else '(none)'}"
    except RuntimeError as e:
        return str(e)


if __name__ == "__main__":
    mcp.run()
