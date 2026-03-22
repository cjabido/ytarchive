# MCP Server Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a FastMCP stdio server that exposes YTArchive's FastAPI backend as five MCP tools for Claude Code AI agents.

**Architecture:** Single-file Python MCP server (`mcp-server/server.py`) using FastMCP and httpx to proxy all data operations through the existing REST API at `localhost:8000`. No direct SQLite access, no LLM calls — the calling agent provides all reasoning.

**Tech Stack:** Python 3.11+, FastMCP, httpx, pytest + pytest-asyncio + respx (HTTP mocking)

---

## Chunk 1: Project scaffold and error helper

### Task 1: Create project scaffold

**Files:**
- Create: `mcp-server/requirements.txt`
- Create: `mcp-server/requirements-dev.txt`
- Create: `mcp-server/server.py` (scaffold only — imports and app init)

- [ ] **Step 1: Create `mcp-server/requirements.txt`**

```
fastmcp>=2.0
httpx>=0.27
```

- [ ] **Step 2: Create `mcp-server/requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0
pytest-asyncio>=0.23
respx>=0.21
```

- [ ] **Step 3: Create the venv and install deps**

```bash
cd "mcp-server"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Expected: packages install without errors.

- [ ] **Step 4: Create `mcp-server/server.py` scaffold**

```python
"""
YTArchive MCP Server

Exposes the YTArchive FastAPI backend as MCP tools for Claude Code agents.
Transport: stdio (local agents only).
All data operations proxy through http://localhost:8000.
"""

import httpx
from fastmcp import FastMCP

BASE_URL = "http://localhost:8000/api"

mcp = FastMCP("ytarchive")


# ── HTTP helper ──────────────────────────────────────────────────────────────

async def _get(path: str, **params) -> dict:
    """GET request to the backend. Raises on non-2xx."""
    filtered = {k: v for k, v in params.items() if v is not None}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{BASE_URL}{path}", params=filtered)
    except httpx.ConnectError:
        raise RuntimeError(
            "Backend unavailable at localhost:8000 — ensure the FastAPI server is running."
        )
    if r.status_code == 404:
        raise RuntimeError(f"Not found: {path}")
    if not r.is_success:
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise RuntimeError(f"Backend error {r.status_code}: {detail}")
    return r.json()


async def _post(path: str, body: dict) -> dict:
    """POST request to the backend."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{BASE_URL}{path}", json=body)
    except httpx.ConnectError:
        raise RuntimeError(
            "Backend unavailable at localhost:8000 — ensure the FastAPI server is running."
        )
    if not r.is_success:
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise RuntimeError(f"Backend error {r.status_code}: {detail}")
    return r.json()


async def _put(path: str, body: dict) -> dict:
    """PUT request to the backend."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.put(f"{BASE_URL}{path}", json=body)
    except httpx.ConnectError:
        raise RuntimeError(
            "Backend unavailable at localhost:8000 — ensure the FastAPI server is running."
        )
    if not r.is_success:
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise RuntimeError(f"Backend error {r.status_code}: {detail}")
    return r.json()


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 5: Verify syntax**

```bash
cd "mcp-server" && .venv/bin/python -m py_compile server.py && echo "OK"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add mcp-server/
git commit -m "feat: scaffold MCP server with HTTP helpers"
```

---

## Chunk 2: Read tools (list_videos, list_tags, get_video_details)

### Task 2: `ytarchive_list_tags`

**Files:**
- Modify: `mcp-server/server.py`
- Create: `mcp-server/tests/test_list_tags.py`

- [ ] **Step 1: Create test file**

```python
# mcp-server/tests/test_list_tags.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp-server && .venv/bin/pytest tests/test_list_tags.py -v
```

Expected: FAIL — `ytarchive_list_tags` tool not found.

- [ ] **Step 3: Add `ytarchive_list_tags` tool to `server.py`**

Add after the HTTP helpers:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd mcp-server && .venv/bin/pytest tests/test_list_tags.py -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add mcp-server/server.py mcp-server/tests/
git commit -m "feat: add ytarchive_list_tags MCP tool"
```

---

### Task 3: `ytarchive_list_videos`

**Files:**
- Modify: `mcp-server/server.py`
- Create: `mcp-server/tests/test_list_videos.py`

- [ ] **Step 1: Create test file**

```python
# mcp-server/tests/test_list_videos.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp-server && .venv/bin/pytest tests/test_list_videos.py -v
```

Expected: FAIL

- [ ] **Step 3: Add `ytarchive_list_videos` tool to `server.py`**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
cd mcp-server && .venv/bin/pytest tests/test_list_videos.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add mcp-server/server.py mcp-server/tests/test_list_videos.py
git commit -m "feat: add ytarchive_list_videos MCP tool"
```

---

### Task 4: `ytarchive_get_video_details`

**Files:**
- Modify: `mcp-server/server.py`
- Create: `mcp-server/tests/test_get_video_details.py`

- [ ] **Step 1: Create test file**

```python
# mcp-server/tests/test_get_video_details.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp-server && .venv/bin/pytest tests/test_get_video_details.py -v
```

Expected: FAIL

- [ ] **Step 3: Add `ytarchive_get_video_details` tool to `server.py`**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
cd mcp-server && .venv/bin/pytest tests/test_get_video_details.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add mcp-server/server.py mcp-server/tests/test_get_video_details.py
git commit -m "feat: add ytarchive_get_video_details MCP tool"
```

---

## Chunk 3: Write tools (add_watch_history, set_video_tags)

### Task 5: `ytarchive_add_watch_history`

**Files:**
- Modify: `mcp-server/server.py`
- Create: `mcp-server/tests/test_add_watch_history.py`

- [ ] **Step 1: Create test file**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp-server && .venv/bin/pytest tests/test_add_watch_history.py -v
```

Expected: FAIL

- [ ] **Step 3: Add `ytarchive_add_watch_history` tool to `server.py`**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
cd mcp-server && .venv/bin/pytest tests/test_add_watch_history.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add mcp-server/server.py mcp-server/tests/test_add_watch_history.py
git commit -m "feat: add ytarchive_add_watch_history MCP tool"
```

---

### Task 6: `ytarchive_set_video_tags`

**Files:**
- Modify: `mcp-server/server.py`
- Create: `mcp-server/tests/test_set_video_tags.py`

- [ ] **Step 1: Create test file**

```python
# mcp-server/tests/test_set_video_tags.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp-server && .venv/bin/pytest tests/test_set_video_tags.py -v
```

Expected: FAIL

- [ ] **Step 3: Add `ytarchive_set_video_tags` tool to `server.py`**

```python
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
```

- [ ] **Step 4: Run all tests**

```bash
cd mcp-server && .venv/bin/pytest tests/ -v
```

Expected: all 15 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add mcp-server/server.py mcp-server/tests/test_set_video_tags.py
git commit -m "feat: add ytarchive_set_video_tags MCP tool"
```

---

## Chunk 4: pytest config and Claude Code integration

### Task 7: Pytest config and test runner

**Files:**
- Create: `mcp-server/pytest.ini`
- Create: `mcp-server/tests/__init__.py`

- [ ] **Step 1: Create `mcp-server/tests/__init__.py`**

Empty file — makes `tests/` a proper package so imports resolve correctly.

```bash
touch "mcp-server/tests/__init__.py"
```

- [ ] **Step 2: Create `mcp-server/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

`asyncio_mode = auto` means every async test function is automatically treated as an asyncio coroutine by pytest-asyncio — no decorator needed on individual test functions.

- [ ] **Step 3: Run full suite to confirm clean pass**

```bash
cd mcp-server && .venv/bin/pytest -v
```

Expected: all tests PASSED, no warnings about missing asyncio mode.

- [ ] **Step 4: Commit**

```bash
git add mcp-server/pytest.ini mcp-server/tests/__init__.py
git commit -m "test: add pytest config for MCP server tests"
```

---

### Task 8: Wire Claude Code MCP config

**Files:**
- Modify: `.claude/settings.json` (project-level, create if absent)

- [ ] **Step 1: Get the absolute project path**

```bash
pwd
```

Note the output — this is `<PROJECT_ROOT>`.

- [ ] **Step 2: Update `.claude/settings.json`**

Add or merge the `mcpServers` block. Replace `<PROJECT_ROOT>` with the actual path from step 1:

```json
{
  "mcpServers": {
    "ytarchive": {
      "command": "<PROJECT_ROOT>/mcp-server/.venv/bin/python",
      "args": ["<PROJECT_ROOT>/mcp-server/server.py"]
    }
  }
}
```

If `.claude/settings.json` doesn't exist yet, create it with just this content.

- [ ] **Step 3: Restart Claude Code and verify the server appears**

In Claude Code, run `/mcp` — `ytarchive` should appear as a connected server with 5 tools listed:
- `ytarchive_add_watch_history`
- `ytarchive_list_videos`
- `ytarchive_list_tags`
- `ytarchive_get_video_details`
- `ytarchive_set_video_tags`

If the server doesn't appear, check:
1. Backend is running: `curl http://localhost:8000/api/tags`
2. Python path is correct: `<PROJECT_ROOT>/mcp-server/.venv/bin/python --version`
3. Server syntax: `<PROJECT_ROOT>/mcp-server/.venv/bin/python -m py_compile <PROJECT_ROOT>/mcp-server/server.py`

- [ ] **Step 4: Commit**

```bash
git add .claude/settings.json
git commit -m "config: register ytarchive MCP server with Claude Code"
```

---

## Verification

After all tasks complete, run the full test suite one final time:

```bash
cd mcp-server && .venv/bin/pytest -v --tb=short
```

Expected output: 15 tests, all green.

Then smoke-test the live server with the backend running:

```bash
# In one terminal: ensure backend is up
cd backend && uvicorn main:app --reload

# In another terminal: verify MCP server starts without error
cd mcp-server && .venv/bin/python server.py
# Should hang waiting for stdio input — Ctrl+C to exit
```
