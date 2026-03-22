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


if __name__ == "__main__":
    mcp.run()
