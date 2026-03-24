# Channel Filter Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users click a channel name on any video card to filter the library to that channel, with a dismissible chip to clear the filter.

**Architecture:** Add `channel_exact` query param to the existing `GET /videos` backend endpoint (exact match vs existing fuzzy `channel`). On the frontend, add `filterChannel` state to Library, make channel names clickable in VideoRow, and render a filter chip when active.

**Tech Stack:** FastAPI (Python), React, TailwindCSS, React Query

**Spec:** `docs/superpowers/specs/2026-03-23-channel-filter-design.md`

---

## Chunk 1: Implementation

### Task 1: Add `channel_exact` param to backend

**Files:**
- Modify: `backend/routers/videos.py:22-44`

- [ ] **Step 1: Add the parameter and condition**

In the `list_videos` function signature (line 22-34), add `channel_exact` after the existing `channel` param:

```python
@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    q: Optional[str] = None,
    channel: Optional[str] = None,
    channel_exact: Optional[str] = None,
    tag: Optional[str] = None,
    # ... rest unchanged
```

After the existing `channel` condition block (line 42-44), add:

```python
    if channel_exact:
        conditions.append("c.channel_name = ?")
        params.append(channel_exact)
```

- [ ] **Step 2: Verify backend starts**

Run: `cd backend && source venv/bin/activate && python -c "from routers.videos import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/routers/videos.py
git commit -m "feat: add channel_exact param to GET /videos for exact channel filtering"
```

---

### Task 2: Add channel filter state and query wiring in Library

**Files:**
- Modify: `frontend/src/pages/Library.jsx:3,32-47`

- [ ] **Step 1: Add X icon import**

At line 3, add `X` to the lucide-react import:

```javascript
import { Search, BookOpen, ChevronLeft, ChevronRight, Eye, RefreshCw, FileText, X } from 'lucide-react'
```

- [ ] **Step 2: Add filterChannel state**

After `const [selectedVideoId, setSelectedVideoId] = useState(null)` (line 39), add:

```javascript
  const [filterChannel, setFilterChannel] = useState('')
```

- [ ] **Step 3: Wire filterChannel into useQuery**

Update the useQuery call (lines 43-47) to include `filterChannel` in the key and pass `channel_exact`:

```javascript
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['videos', debouncedQ, filterTag, filterStatus, filterChannel, sort, page],
    queryFn: () => fetchVideos({ q: debouncedQ, tag: filterTag, watchlist_status: filterStatus, channel_exact: filterChannel, sort, page, per_page: 50 }),
    keepPreviousData: true,
  })
```

- [ ] **Step 4: Add handleChannelClick handler**

After the `setFilter` helper (line 55-57), add:

```javascript
  function handleChannelClick(channelName) {
    setFilterChannel(channelName)
    setSearch('')
    setDebouncedQ('')
    setFilterTag('')
    setFilterStatus('')
    setPage(1)
  }
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Library.jsx
git commit -m "feat: add channel filter state and query wiring to Library"
```

---

### Task 3: Make channel name clickable in VideoRow

**Files:**
- Modify: `frontend/src/pages/Library.jsx:168-174,240,258-259`

- [ ] **Step 1: Pass onChannelClick to VideoRow**

Update the VideoRow render (lines 168-174) to pass the handler:

```jsx
              <VideoRow
                key={v.video_id}
                video={v}
                index={i}
                onClick={() => setSelectedVideoId(v.video_id)}
                onChannelClick={handleChannelClick}
              />
```

- [ ] **Step 2: Update VideoRow to accept and use onChannelClick**

Update the VideoRow function signature (line 240):

```javascript
function VideoRow({ video, index, onClick, onChannelClick }) {
```

Replace the channel name `<span>` (line 259):

```jsx
          <span className="text-xs text-text-muted truncate">{video.channel_name}</span>
```

With a clickable button:

```jsx
          <button
            onClick={(e) => { e.stopPropagation(); onChannelClick(video.channel_name) }}
            className="text-xs text-text-muted truncate hover:text-accent-sky transition-colors cursor-pointer"
          >
            {video.channel_name}
          </button>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Library.jsx
git commit -m "feat: make channel name clickable to filter by channel"
```

---

### Task 4: Add dismissible channel filter chip

**Files:**
- Modify: `frontend/src/pages/Library.jsx:146-148`

- [ ] **Step 1: Add the chip between filters row and video list**

After the closing `</div>` of the filters row (line 146) and before the `{/* Video list */}` comment (line 148), add:

```jsx
        {/* Channel filter chip */}
        {filterChannel && (
          <div className="flex items-center gap-2 animate-fade-in-up">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-sky-dim text-accent-sky text-xs font-medium">
              Showing videos from {filterChannel}
              <button
                onClick={() => setFilterChannel('')}
                className="hover:text-text-primary transition-colors cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
          </div>
        )}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Library.jsx
git commit -m "feat: add dismissible channel filter chip"
```

---

### Task 5: Manual verification

- [ ] **Step 1: Start backend and frontend**

```bash
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8001 &
cd frontend && npm run dev -- --port 3001
```

- [ ] **Step 2: Verify all behaviors**

Open `http://localhost:3001` and check:
- Click a channel name on a video card → list filters to that channel, other filters clear
- Chip appears with "Showing videos from [Channel Name]"
- Click ✕ on chip → returns to full unfiltered list
- Click a different channel while one is active → switches filter
- Video detail panel still opens when clicking the row body (not the channel name)
- Pagination resets to page 1 when filtering

- [ ] **Step 3: Final commit (if any fixups needed)**
