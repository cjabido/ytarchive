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

### 3. Channel click handler (defined in Library, passed to VideoRow)

Define `handleChannelClick(channelName)` in `Library` as a closure over the state setters:
- Sets `filterChannel` to the channel name
- Clears `search` to `''` and immediately resets the debounced value (call `setDebouncedQ('')` — note: the debounce hook delays by 300ms, so the query will briefly use the stale `debouncedQ` before it clears; this is acceptable since the `channel_exact` filter dominates the results)
- Clears `filterTag` and `filterStatus` to `''`
- Resets `page` to 1

Pass this handler to `VideoRow` as the `onChannelClick` prop.

### 4. Clickable channel name in VideoRow

`VideoRow` currently accepts `{ video, index, onClick }`. Add `onChannelClick` to the destructured props.

The channel name `<span>` at line 259 becomes a `<button>`. Clicking it calls `onChannelClick(video.channel_name)` with `e.stopPropagation()` so the row's `onClick` (video detail) doesn't fire.

### 5. Active filter chip

When `filterChannel` is set, render a dismissible chip above the video list (before the video list, after the filters row):

```
[Showing videos from Channel Name ✕]
```

Clicking ✕ clears `filterChannel`.

Styled as a pill with `bg-accent-sky-dim text-accent-sky` to match the Library's color scheme.

### 6. Backend param coexistence

The existing `channel` (fuzzy) param is not exposed in the UI currently. If both `channel` and `channel_exact` are sent, both conditions apply (AND). This is acceptable — in practice only `channel_exact` will be sent from the UI.

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
