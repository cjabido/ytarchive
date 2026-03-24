# Filter Library by Channel

## Summary

Add the ability to filter the video library by channel. Clicking a channel name on any video card filters the list to show only videos from that channel, replacing any active filters. A dismissible chip indicates the active channel filter.

## Scope

This is a minimal feature — primarily a frontend change with one small backend addition.

## Backend Change

**`GET /videos` — add `channel_exact` parameter**

The existing `channel` param does a fuzzy `LIKE %name%` match. Add a new `channel_exact` param that does an exact match (`c.channel_name = ?`). The clickable channel name in the UI will use `channel_exact` to avoid false matches (e.g., "MKBHD" matching "MKBHD Clips").

- File: `backend/routers/videos.py`
- Add `channel_exact: Optional[str] = None` to `list_videos` signature
- Add condition: `c.channel_name = ?` when `channel_exact` is provided
- No new endpoints, models, or migrations

## Frontend Changes

All changes in `frontend/src/pages/Library.jsx`:

### 1. New state

```javascript
const [filterChannel, setFilterChannel] = useState('')
```

### 2. Wire into query

Add `filterChannel` to the `useQuery` key and pass as `channel_exact` to `fetchVideos`:

```javascript
queryKey: ['videos', debouncedQ, filterTag, filterStatus, filterChannel, sort, page],
queryFn: () => fetchVideos({
  q: debouncedQ, tag: filterTag, watchlist_status: filterStatus,
  channel_exact: filterChannel, sort, page, per_page: 50
}),
```

### 3. Clickable channel name in VideoRow

The channel name span becomes a button. Clicking it:
- Sets `filterChannel` to the channel name
- Clears `search`, `debouncedQ`, `filterTag`, `filterStatus`
- Resets `page` to 1
- Stops event propagation (so the row click for video detail doesn't fire)

### 4. Active filter chip

When `filterChannel` is set, render a chip above the video list:

```
[Showing videos from Channel Name ✕]
```

Clicking ✕ clears `filterChannel`.

Styled as a pill with `bg-accent-sky-dim text-accent-sky` to match the Library's color scheme.

### 5. Pass channel click handler to VideoRow

VideoRow receives an `onChannelClick` prop. The channel name element calls `onChannelClick(video.channel_name)` with `e.stopPropagation()`.

## What doesn't change

- No new pages, routes, or navigation items
- No new API endpoints or files
- No database/migration changes
- No new frontend components or files
- `api.js` — `fetchVideos` already passes all params through, so `channel_exact` works automatically

## Testing

- Click a channel name → list filters to that channel only, other filters clear
- Chip displays with correct channel name
- Click ✕ on chip → returns to unfiltered list
- Clicking a different channel while one is active → switches to new channel
- Pagination resets to page 1 on channel filter
- Video detail still opens when clicking the row (not the channel name)
