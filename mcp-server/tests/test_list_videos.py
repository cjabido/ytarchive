import pytest
import respx
import httpx
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from server import mcp

BASE = "http://localhost:8000/api"

MOCK_RESPONSE = {
    "total": 1, "page": 1, "per_page": 50,
    "videos": [{
        "video_id": "abc123",
        "video_title": "Learn Python",
        "channel_name": "CodeChannel",
        "last_watched": "2026-03-20T10:00:00",
        "watch_count": 3,
        "tags": [{"id": 1, "name": "Python"}],
    }]
}

async def test_list_videos_no_filters():
    with respx.mock(base_url=BASE) as mock:
        mock.get("/videos").mock(return_value=httpx.Response(200, json=MOCK_RESPONSE))
        result = await mcp.call_tool("ytarchive_list_videos", {})
    assert "Learn Python" in result.content[0].text

async def test_list_videos_with_query():
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/videos").mock(return_value=httpx.Response(200, json=MOCK_RESPONSE))
        await mcp.call_tool("ytarchive_list_videos", {"q": "Python"})
    assert route.called
    assert route.calls[0].request.url.params["q"] == "Python"

async def test_list_videos_backend_unavailable():
    with respx.mock(base_url=BASE) as mock:
        mock.get("/videos").mock(side_effect=httpx.ConnectError("refused"))
        result = await mcp.call_tool("ytarchive_list_videos", {})
    assert "unavailable" in result.content[0].text.lower()
