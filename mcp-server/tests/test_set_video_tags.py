import pytest
import respx
import httpx
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from server import mcp

BASE = "http://localhost:8000/api"

async def test_set_video_tags_applies_tags():
    with respx.mock(base_url=BASE) as mock:
        mock.put("/videos/abc123/tags").mock(return_value=httpx.Response(200, json={
            "video_id": "abc123",
            "tags": [{"id": 1, "name": "Python"}, {"id": 2, "name": "Tutorial"}],
        }))
        result = await mcp.call_tool("ytarchive_set_video_tags", {
            "video_id": "abc123",
            "tag_ids": [1, 2],
        })
    assert "Python" in result.content[0].text
    assert "Tutorial" in result.content[0].text

async def test_set_video_tags_enforces_max_5():
    result = await mcp.call_tool("ytarchive_set_video_tags", {
        "video_id": "abc123",
        "tag_ids": [1, 2, 3, 4, 5, 6],
    })
    assert "maximum" in result.content[0].text.lower() or "5" in result.content[0].text

async def test_set_video_tags_exactly_5_is_allowed():
    with respx.mock(base_url=BASE) as mock:
        mock.put("/videos/abc123/tags").mock(return_value=httpx.Response(200, json={
            "video_id": "abc123",
            "tags": [{"id": i, "name": f"Tag{i}"} for i in range(1, 6)],
        }))
        result = await mcp.call_tool("ytarchive_set_video_tags", {
            "video_id": "abc123",
            "tag_ids": [1, 2, 3, 4, 5],
        })
    assert "Tag1" in result.content[0].text

async def test_set_video_tags_video_not_found():
    with respx.mock(base_url=BASE) as mock:
        mock.put("/videos/missing/tags").mock(return_value=httpx.Response(404))
        result = await mcp.call_tool("ytarchive_set_video_tags", {
            "video_id": "missing",
            "tag_ids": [1],
        })
    assert "not found" in result.content[0].text.lower()

async def test_set_video_tags_backend_unavailable():
    with respx.mock(base_url=BASE) as mock:
        mock.put("/videos/abc123/tags").mock(side_effect=httpx.ConnectError("refused"))
        result = await mcp.call_tool("ytarchive_set_video_tags", {
            "video_id": "abc123",
            "tag_ids": [1],
        })
    assert "unavailable" in result.content[0].text.lower()
