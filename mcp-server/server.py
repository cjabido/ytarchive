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


if __name__ == "__main__":
    mcp.run()
