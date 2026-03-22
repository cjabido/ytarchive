# mcp-server/tests/test_add_watch_history.py
import pytest
import respx
import httpx
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from server import mcp

BASE = "http://localhost:8000/api"

MOCK_UPSERT = {"video_id": "abc123", "video_title": "Learn Python", "watched_at": "2026-03-22T10:00:00"}

async def test_add_watch_history_minimal():
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/videos").mock(return_value=httpx.Response(200, json=MOCK_UPSERT))
        result = await mcp.call_tool("ytarchive_add_watch_history", {
            "video_id": "abc123",
            "video_title": "Learn Python",
            "video_url": "https://youtube.com/watch?v=abc123",
        })
    assert "abc123" in result.content[0].text
    body = route.calls[0].request
    import json
    sent = json.loads(body.content)
    assert sent["video_id"] == "abc123"
    assert sent.get("fetch_transcript") is False

async def test_add_watch_history_with_fetch_transcript():
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/videos").mock(return_value=httpx.Response(200, json=MOCK_UPSERT))
        await mcp.call_tool("ytarchive_add_watch_history", {
            "video_id": "abc123",
            "video_title": "Learn Python",
            "video_url": "https://youtube.com/watch?v=abc123",
            "fetch_transcript": True,
        })
    import json
    sent = json.loads(route.calls[0].request.content)
    assert sent["fetch_transcript"] is True

async def test_add_watch_history_backend_unavailable():
    with respx.mock(base_url=BASE) as mock:
        mock.post("/videos").mock(side_effect=httpx.ConnectError("refused"))
        result = await mcp.call_tool("ytarchive_add_watch_history", {
            "video_id": "abc123",
            "video_title": "Learn Python",
            "video_url": "https://youtube.com/watch?v=abc123",
        })
    assert "unavailable" in result.content[0].text.lower()
