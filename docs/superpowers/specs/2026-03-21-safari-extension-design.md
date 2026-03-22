# Safari Extension Design — YTArchive

**Date:** 2026-03-21
**Status:** Approved
**Project:** YTArchive — Phase 3

---

## Overview

A Safari WebExtension (Manifest v3) popup on `youtube.com/watch?v=*` for capturing YouTube videos directly into a local archive — no Google Takeout required.

---

## Architecture

### Message Flow

```
  popup.js            ← opens on icon click
        │  chrome.tabs.sendMessage({ type: 'GET_VIDEO_INFO' })
        ▼
  content.js          ← parses ytInitialData, calls sendResponse(data)
        │  async response (return true pattern)
        ▼
  popup.js continues
        │  fetch()
        ▼
  localhost:8000/api
```

### Files

```
safari-extension/
├── config.js          ← imported by popup.js only (classic script)
├── manifest.json
├── background.js      ← badge state only
├── content.js
├── popup/
│   ├── popup.html
│   ├── popup.js       ← classic script (not type="module")
│   └── popup.css
└── icons/
    ├── 16.png
    ├── 48.png
    └── 128.png
```

### Async Message Pattern

`extractVideoInfo()` reads the DOM and `ytInitialData` **synchronously** — no network calls, no polling. It is wrapped in a Promise purely for consistency with the message pattern. `return true` is required to keep the channel open for the `.then(sendResponse)` microtask tick.

```js
// content.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_VIDEO_INFO') {
    extractVideoInfo().then(sendResponse);
    return true; // keep channel open for the microtask
  }
});

// popup.js
const info = await chrome.tabs.sendMessage(tab.id, { type: 'GET_VIDEO_INFO' });
```

**`ytInitialData` availability:** By the time the badge fires (`status=complete`) and the user opens the popup, `ytInitialData` should already be assigned by YouTube's page script. If it is `undefined` or the expected path is missing at read time, `channel_name` and `channel_url` are returned as `null` — treated as a silent omission, not a hard error. No polling or retry in `content.js`; the user can still save with null channel fields.

**Async handler reliability:** To avoid any Safari-specific `return true` race, use the following explicit async pattern:
```js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_VIDEO_INFO') {
    (async () => { sendResponse(await extractVideoInfo()); })();
    return true;
  }
});
```
The IIFE invokes `extractVideoInfo()` (which resolves synchronously via `Promise.resolve(data)`) and calls `sendResponse` before the microtask queue yields.

---

## Configuration

```js
// safari-extension/config.js
// To use over Tailscale, change this to your Mac's Tailscale address
const CONFIG = {
  API_BASE_URL: 'http://localhost:8000'
};
```

**Script loading:** Both `config.js` and `popup.js` are classic scripts (no `type="module"`). `config.js` sets `CONFIG` on `window`; `popup.js` reads `CONFIG` directly.

```html
<!-- popup/popup.html — config.js must come first -->
<script src="../config.js"></script>
<script src="popup.js"></script>
```

**`config.js` is NOT injected into content scripts** — `content.js` makes no API calls and does not use `CONFIG`.

```json
// manifest.json content_scripts
"content_scripts": [{
  "matches": ["*://www.youtube.com/watch*"],
  "js": ["content.js"]
}]
```

`config.js` does not need to appear in `web_accessible_resources` — it is only loaded by the extension's own popup page.

Documented in `safari-extension/README.md`.

---

## Content Script — Data Extraction

`content.js` reads page data synchronously inside `extractVideoInfo()`, which returns a Promise (async wrapper for consistency with the message pattern).

| Field | Source | Fallback |
|---|---|---|
| `video_id` | `new URLSearchParams(window.location.search).get('v')` | `null` |
| `video_title` | `document.title` stripped of `" - YouTube"` | `null` |
| `channel_name` | `ytInitialData → videoOwnerRenderer.title.runs[0].text` | `null` |
| `channel_url` | `ytInitialData → videoOwnerRenderer.navigationEndpoint...canonicalBaseUrl` | `null` |
| `video_url` | `window.location.href` | — |
| `watched_at` | *(not set in content.js — set in popup.js at save time)* | — |

**`watched_at` is captured in `popup.js` at the moment Save is clicked** (`new Date().toISOString()`), not in `content.js`. This avoids skew when the user leaves the popup open before saving.

If `ytInitialData` parsing fails or the path is absent, `channel_name` and `channel_url` are `null`. Popup still allows saving — channel fields are optional.

**No `?v=` param:** When there is no `v` query param, `video_id` is returned as `null`. All other fields may also be null. `popup.js` checks `info.video_id === null` after receiving the response and renders the "Not a video" state immediately — no further API calls are made.

---

## Background Service Worker

`background.js` manages the extension icon badge. YouTube is a SPA — URL changes via `history.pushState` do not trigger `status=complete`. Both events must be handled.

```js
const isYouTubeVideo = (url) =>
  !!url && url.includes('youtube.com/watch') && new URL(url).searchParams.has('v');

const updateBadge = (tabId, url) => {
  if (isYouTubeVideo(url)) {
    chrome.action.setBadgeText({ text: '●', tabId });
    chrome.action.setBadgeBackgroundColor({ color: '#10b981', tabId });
  } else {
    chrome.action.setBadgeText({ text: '', tabId });
  }
};

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Handle both SPA url changes and hard-load completions
  const url = changeInfo.url || (changeInfo.status === 'complete' ? tab.url : null);
  if (url) updateBadge(tabId, url);
});
```

No other logic in `background.js`.

---

## UI Design

### Visual Style

Arctic Ledger design system: `#f4f4f7` page background, `#ffffff` card surfaces, `#1a1a2e` text, DM Sans font, `#0284c7` (sky) for primary actions, `#10b981` (mint) for success/positive, `#7c3aed` (violet) for tag pills.

### Layout (300px wide, approved in brainstorm)

```
┌─────────────────────────────┐  ← 3px gradient (red → sky → violet)
│ [YT icon] YouTube           │  ← source row, own line
├─────────────────────────────┤
│ [thumb]  Title (2-line max) │  ← thumbnail: img.youtube.com/vi/{id}/hqdefault.jpg
│          Channel name       │
├─────────────────────────────┤
│ to-rewatch │[reference]│ .. │  ← watchlist status pills
├─────────────────────────────┤
│ Tags: [ml] [ref] [+ add ▾]  │  ← toggleable pills, click to remove
│ Notes: ________________     │
├─────────────────────────────┤
│ ≡ Fetch Transcript [●InDB] [Save] │
└─────────────────────────────┘
```

### Watchlist Status Pills

| Pill label | `watchlist_status` value in POST |
|---|---|
| to-rewatch | `to-rewatch` |
| reference | `reference` |
| download | `to-download` ← note: wire value differs from label |
| done | `done` |
| *(none selected)* | field omitted from payload |

The right-hand column is the exact string sent in the API payload. One pill active at a time. Tapping an active pill deselects it (field omitted from POST).

**Note on GET/POST field name asymmetry:** `GET /api/videos/{id}` returns `response.watchlist.status` (nested). `POST /api/videos` accepts `watchlist_status` (flat, top-level). Pre-fill:
```js
const status = response.watchlist?.status ?? null;
```

### Tag Picker

- Shows existing tags from `GET /api/tags` only — no free-text input, no new tag creation
- Selected tags shown as violet pills; click a pill to **remove** it
- `[+ add ▾]` opens an inline dropdown listing unselected tags (with their `color`)
- If `GET /api/tags` fails: show "Tags unavailable" in the tag section, save proceeds with `tags: []`

### Fetch Transcript Link

Text link in footer. Independent of Save **except** during Saving state and for new (unsaved) videos:

| State | Label | Enabled? | Behavior |
|---|---|---|---|
| New video, not yet saved | "Fetch Transcript" | **Disabled** | Video must exist in DB before transcript can be fetched |
| Already saved, `has_transcript: false` | "Fetch Transcript" | Enabled | Fire POST, show "Fetching…" 1.5s, revert |
| Already saved, `has_transcript: true` | "Re-fetch Transcript" | Enabled | Fire POST, show "Fetching…" 1.5s, revert |
| Saving state (spinner active) | any | **Disabled** | Re-enable after save completes or fails |
| POST returns error | any | Enabled | Show "Transcript unavailable" 2s, revert |

**New video ordering rule:** Fetch Transcript is disabled until a successful save (201) promotes the video to "Already saved" state. After Save succeeds and the popup would normally close — if the user had clicked Fetch Transcript just before saving, fire the transcript fetch in the same close sequence.

`fetch_transcript` in the `POST /api/videos` payload is always `false`. A transcript fetch triggered via the link (`POST /api/transcripts/{id}/fetch`) runs as an independent background job on the server — a subsequent `POST /api/videos` upsert with `fetch_transcript: false` does not cancel or interfere with it.

---

## Popup States

| State | Trigger | UI |
|---|---|---|
| **Loading** | Popup opens | Shimmer for title/channel/tags; 10s timeout → Error state |
| **New video** | 404 from GET | Blank form, "Save to Archive" button |
| **Already saved** | 200 from GET | Pre-filled form (see below), "In DB" badge, "Update" button |
| **Saving** | Save clicked | Button disabled + spinner |
| **Success** | 201 or 200 from POST | Popup closes automatically — intentional for both create and update flows |
| **Error** | Network/5xx on save, or load timeout | Inline error, "Save Offline" button, primary button re-enabled |
| **Not a video** | `video_id` is `null` | "Open a YouTube video to use this extension" — skip all API calls |

**Loading timeout:** If `GET /api/videos/{id}` or `GET /api/tags` does not respond within 10 seconds, transition to Error state with message "Couldn't connect to archive — is the server running?"

**"Not a video" state:** When `video_id` is `null`, **do not issue any API calls**. Render the message immediately.

### "Already saved" Pre-fill

When `GET /api/videos/{id}` returns 200:

| UI element | Source in response |
|---|---|
| Tags | `response.tags` (array of `{name, color}` — match to existing tag pills) |
| Status pill | `response.watchlist?.status ?? null` |
| Notes textarea | `response.notes ?? ''` |
| Fetch Transcript label | `response.has_transcript` → "Re-fetch Transcript" if true |

"Update" button calls the same `POST /api/videos` endpoint (upsert). No PUT/PATCH needed.

---

## Offline Fallback

On network error or 5xx response to save:

1. "Save Offline" button appears alongside the error message
2. Clicking it appends the video payload to `chrome.storage.local` `pendingQueue` array — **storage is written before the popup closes**
3. Shows "Saved locally — open popup when your server is running to sync"
4. Popup closes

**On next popup open** (before rendering current video):

1. Read `pendingQueue` from `chrome.storage.local`
2. If non-empty: show "X items pending sync" notice at top
3. Flush in order, one item at a time:
   - **Success (201/200):** remove item from queue, update storage, continue to next
   - **4xx:** drop item (unrecoverable payload error), log to console, update storage, continue
   - **5xx or network error:** move item to the **end** of the queue (so subsequent items get a retry chance), increment its `retryCount`; if `retryCount >= 3`, drop it instead and log "Dropped after 3 failed attempts"; update storage; stop flush for this session — retain all remaining items
4. Each storage write happens immediately after each item result, before proceeding — partial flushes are always persisted even if popup is closed mid-flush
5. If queue empties: remove "pending sync" notice

Each queued item carries a `retryCount` field (default `0`) incremented on each 5xx/network failure. This prevents a permanently broken item from blocking the queue forever.

---

## API Calls

| When | Call | Notes |
|---|---|---|
| Popup opens (if video_id non-null) | `GET /api/videos/{video_id}` | 200 = pre-fill, 404 = blank |
| Popup opens (if video_id non-null) | `GET /api/tags` | Populate tag picker |
| Save clicked | `POST /api/videos` | 201 = created, 200 = upserted |
| Save clicked (already saved + all pills deselected) | `DELETE /api/watchlist/{video_id}` | Backend cannot clear status via POST — must call separately after POST succeeds |
| Transcript link clicked | `POST /api/transcripts/{video_id}/fetch` | 202 = queued |

**POST /api/videos payload:**
```json
{
  "video_id": "...",
  "video_title": "...",
  "video_url": "...",
  "channel_name": "...",
  "channel_url": "...",
  "watched_at": "2026-03-21T14:30:00.000Z",
  "tags": ["reference", "ml"],
  "watchlist_status": "reference",
  "notes": "...",
  "fetch_transcript": false
}
```

Field rules:
- `channel_name`, `channel_url`: may be `null` if ytInitialData parsing failed
- `watchlist_status`: omitted entirely if no pill selected
- `tags`: `[]` if no tags selected
- `notes`: omit if the textarea is empty. **Backend limitation:** `POST /api/videos` only writes notes when `body.notes` is truthy (`if body.notes:`) — sending `null` or `""` is a no-op and does not clear existing notes. Clearing notes from the extension is therefore not supported in this phase. Pre-fill uses `response.notes ?? ''`.
- `watchlist_status`: when all pills are deselected on an already-saved video, the extension must call `DELETE /api/watchlist/{video_id}` as a **separate request after the POST** — sending `null` in the POST payload is a no-op (backend only writes `if body.watchlist_status:`). For new videos with no pill selected, simply omit the field.
- `fetch_transcript`: always `false`

---

## Xcode Wrapping

Safari requires a native app wrapper around the WebExtension. One-time setup:

```bash
xcrun safari-web-extension-converter safari-extension/ \
  --project-location . \
  --app-name YTArchive
```

Steps:
1. Run from project root — generates `YTArchive/YTArchive.xcodeproj`
2. Open in Xcode → Build and run (⌘R)
3. Enable in **Safari → Settings → Extensions → YTArchive**
4. Grant permission for `youtube.com`

**When to re-run the converter:**
- `manifest.json` changes
- New files are added to `safari-extension/` (the converter copies the file tree into Xcode)

**For JS/HTML/CSS-only changes:** Do not re-run the converter. Reload the extension in Safari → Settings → Extensions → toggle off then on.

Documented in `safari-extension/README.md`.

---

## Out of Scope

- Options/settings page for API URL (edit `config.js` directly)
- New tag creation from popup (use main web UI)
- Background auto-retry for offline queue
- YouTube API v3 OAuth (Phase 4)
- iOS Safari extension
