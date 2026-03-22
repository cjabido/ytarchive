import pytest
import respx
import httpx
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from server import mcp

BASE = "http://localhost:8000/api"

MOCK_DETAIL = {
    "video_id": "abc123",
    "video_title": "Learn Python",
    "channel_name": "CodeChannel",
    "tags": [{"id": 1, "name": "Python"}],
    "transcript": {"text": "Welcome to Python...", "language": "en", "fetched_at": "2026-03-20T09:00:00"},
    "watch_history": [{"watched_at": "2026-03-20T10:00:00"}],
}

async def test_get_video_details_found():
    with respx.mock(base_url=BASE) as mock:
        mock.get("/videos/abc123").mock(return_value=httpx.Response(200, json=MOCK_DETAIL))
        result = await mcp.call_tool("ytarchive_get_video_details", {"video_id": "abc123"})
    assert "Learn Python" in result.content[0].text
    assert "Welcome to Python" in result.content[0].text

async def test_get_video_details_no_transcript():
    detail = {**MOCK_DETAIL, "transcript": None}
    with respx.mock(base_url=BASE) as mock:
        mock.get("/videos/abc123").mock(return_value=httpx.Response(200, json=detail))
        result = await mcp.call_tool("ytarchive_get_video_details", {"video_id": "abc123"})
    assert "Learn Python" in result.content[0].text

async def test_get_video_details_not_found():
    with respx.mock(base_url=BASE) as mock:
        mock.get("/videos/missing").mock(return_value=httpx.Response(404, json={"detail": "Not found"}))
        result = await mcp.call_tool("ytarchive_get_video_details", {"video_id": "missing"})
    assert "not found" in result.content[0].text.lower()

async def test_get_video_details_backend_unavailable():
    with respx.mock(base_url=BASE) as mock:
        mock.get("/videos/abc123").mock(side_effect=httpx.ConnectError("refused"))
        result = await mcp.call_tool("ytarchive_get_video_details", {"video_id": "abc123"})
    assert "unavailable" in result.content[0].text.lower()
