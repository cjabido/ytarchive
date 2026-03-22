import pytest
import respx
import httpx

# Add server.py to path
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from server import mcp

BASE = "http://localhost:8000/api"

async def test_list_tags_returns_tag_list():
    with respx.mock(base_url=BASE) as mock:
        mock.get("/tags").mock(return_value=httpx.Response(200, json=[
            {"id": 1, "name": "Python", "color": "#3776AB", "video_count": 5},
            {"id": 2, "name": "Music", "color": "#FF6B6B", "video_count": 12},
        ]))
        result = await mcp.call_tool("ytarchive_list_tags", {})
    assert "Python" in result.content[0].text
    assert "Music" in result.content[0].text

async def test_list_tags_backend_unavailable():
    with respx.mock(base_url=BASE) as mock:
        mock.get("/tags").mock(side_effect=httpx.ConnectError("refused"))
        result = await mcp.call_tool("ytarchive_list_tags", {})
    assert "unavailable" in result.content[0].text.lower()
