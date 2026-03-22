# Safari Extension Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Safari WebExtension (MV3) popup that captures YouTube videos from the browser directly into the YTArchive backend — no Google Takeout required.

**Architecture:** A content script reads video data from `ytInitialData` on the YouTube page and responds to a message from the popup. The popup renders the UI, calls the FastAPI backend at `localhost:8000`, and handles offline queueing via `chrome.storage.local`. A background service worker manages the icon badge.

**Tech Stack:** Vanilla JS (classic scripts, no bundler), HTML/CSS (Arctic Ledger tokens), Safari WebExtension MV3, `xcrun safari-web-extension-converter` for Xcode wrapping.

**Spec:** `docs/superpowers/specs/2026-03-21-safari-extension-design.md`

**Security note:** The popup uses safe DOM methods (`createElement`, `textContent`, `appendChild`) for all rendering — no raw innerHTML with user data. `escHtml()` is used exclusively for HTML **attribute values** (e.g. `data-remove-tag`, `data-add-tag`, `data-status` attributes) where the value is set via `setAttribute`. String children passed to the `el()` helper are always inserted as `createTextNode`, not innerHTML.

---

## File Map

| File | Responsibility |
|---|---|
| `safari-extension/config.js` | Single config: `API_BASE_URL`. Edit here for Tailscale. |
| `safari-extension/manifest.json` | MV3 manifest — permissions, content script declaration, popup |
| `safari-extension/background.js` | Badge state only — detects YouTube video URLs, sets/clears badge |
| `safari-extension/content.js` | Extracts video info from `ytInitialData` + DOM, responds to `GET_VIDEO_INFO` |
| `safari-extension/popup/popup.html` | Extension popup shell — loads config.js then popup.js |
| `safari-extension/popup/popup.css` | Arctic Ledger tokens + popup-specific styles |
| `safari-extension/popup/popup.js` | All popup logic: state machine, API calls, offline queue, UI rendering |
| `safari-extension/icons/` | 16/48/128px PNG icons |
| `safari-extension/README.md` | Setup docs: Xcode wrapping, config, reload instructions |

---

## Chunk 1: Scaffold + Manifest + Config

### Task 1: Project scaffold and config

**Files:**
- Create: `safari-extension/config.js`
- Create: `safari-extension/manifest.json`
- Create: `safari-extension/README.md`
- Create: `safari-extension/icons/` (placeholder PNGs)

- [ ] **Step 1: Create the extension directory**

```bash
mkdir -p "safari-extension/icons"
mkdir -p "safari-extension/popup"
```

- [ ] **Step 2: Create `safari-extension/config.js`**

```js
// safari-extension/config.js
// To connect over Tailscale, change API_BASE_URL to your Mac's Tailscale address
// Example: 'http://100.x.x.x:8000'
const CONFIG = {
  API_BASE_URL: 'http://localhost:8000'
};
```

- [ ] **Step 3: Create `safari-extension/manifest.json`**

```json
{
  "manifest_version": 3,
  "name": "YTArchive",
  "version": "1.0",
  "description": "Capture YouTube videos into your local archive",
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/16.png",
      "48": "icons/48.png",
      "128": "icons/128.png"
    }
  },
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["*://www.youtube.com/watch*"],
      "js": ["content.js"]
    }
  ],
  "permissions": [
    "activeTab",
    "tabs",
    "storage"
  ],
  "host_permissions": [
    "*://www.youtube.com/*"
  ]
}
```

- [ ] **Step 4: Create placeholder icons**

Run this from the project root (creates minimal valid PNGs for development):

```bash
python3 -c "
import struct, zlib

def make_png(size):
    def chunk(name, data):
        c = name + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    raw = b''.join(b'\x00\xff\x00\x00' + b'\xff\x00\x00' * size for _ in range(size))
    idat = zlib.compress(raw)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')

for s in [16, 48, 128]:
    with open(f'safari-extension/icons/{s}.png', 'wb') as f:
        f.write(make_png(s))
print('Icons created')
"
```

- [ ] **Step 5: Create `safari-extension/README.md`**

```markdown
# YTArchive Safari Extension

Capture YouTube videos directly into your local YTArchive database.

## Setup (one-time)

1. Make sure the YTArchive backend is running:
   cd backend && python3 -m uvicorn main:app --reload --reload-exclude venv
2. Run the Xcode converter from the project root:
   xcrun safari-web-extension-converter safari-extension/ --project-location . --app-name YTArchive
3. Open YTArchive/YTArchive.xcodeproj in Xcode
4. Build and run (Cmd+R)
5. Enable in Safari -> Settings -> Extensions -> YTArchive
6. Grant permission for youtube.com

## Configuration

Edit safari-extension/config.js to change the backend URL:
  const CONFIG = { API_BASE_URL: 'http://localhost:8000' };

## Reloading after changes

- JS/HTML/CSS changes: Toggle the extension off/on in Safari Settings -> Extensions
- manifest.json changes or new files added: Re-run xcrun safari-web-extension-converter and rebuild in Xcode
```

- [ ] **Step 6: Commit**

```bash
git add safari-extension/
git commit -m "feat: scaffold safari extension — manifest, config, readme"
```

---

## Chunk 2: Background + Content Script

### Task 2: Background badge manager

**Files:**
- Create: `safari-extension/background.js`

- [ ] **Step 1: Create `safari-extension/background.js`**

```js
// safari-extension/background.js
// Manages extension icon badge. Green dot on YouTube video pages, clear otherwise.
// YouTube is a SPA — URL changes via history.pushState do NOT fire status=complete,
// so we handle both changeInfo.url (SPA nav) and changeInfo.status=complete (hard load).

const isYouTubeVideo = (url) =>
  !!url && url.includes('youtube.com/watch') && new URL(url).searchParams.has('v');

const updateBadge = (tabId, url) => {
  if (isYouTubeVideo(url)) {
    chrome.action.setBadgeText({ text: '\u25cf', tabId });
    chrome.action.setBadgeBackgroundColor({ color: '#10b981', tabId });
  } else {
    chrome.action.setBadgeText({ text: '', tabId });
  }
};

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  const url = changeInfo.url || (changeInfo.status === 'complete' ? tab.url : null);
  if (url) updateBadge(tabId, url);
});
```

- [ ] **Step 2: Commit**

```bash
git add safari-extension/background.js
git commit -m "feat: background service worker — youtube video badge"
```

---

### Task 3: Content script — video data extractor

**Files:**
- Create: `safari-extension/content.js`

- [ ] **Step 1: Create `safari-extension/content.js`**

```js
// safari-extension/content.js
// Runs on youtube.com/watch?v=* pages.
// Responds to GET_VIDEO_INFO messages from popup.js.
// No API calls, no use of CONFIG. Reads page DOM and ytInitialData only.

/**
 * Extracts channel info from YouTube's ytInitialData blob.
 * Returns { channel_name, channel_url } or nulls on any parse failure.
 * YouTube restructures this path occasionally — the null fallback is critical.
 */
function extractChannelFromInitialData() {
  try {
    const data = window.ytInitialData;
    if (!data) return { channel_name: null, channel_url: null };

    const contents =
      data?.contents?.twoColumnWatchNextResults?.results?.results?.contents;
    if (!Array.isArray(contents)) return { channel_name: null, channel_url: null };

    for (const item of contents) {
      const owner = item?.videoSecondaryInfoRenderer?.owner?.videoOwnerRenderer;
      if (owner) {
        const channel_name = owner?.title?.runs?.[0]?.text ?? null;
        const baseUrl =
          owner?.navigationEndpoint?.browseEndpoint?.canonicalBaseUrl ?? null;
        const channel_url = baseUrl ? 'https://www.youtube.com' + baseUrl : null;
        return { channel_name, channel_url };
      }
    }
    return { channel_name: null, channel_url: null };
  } catch {
    return { channel_name: null, channel_url: null };
  }
}

/**
 * Extracts video info synchronously from the current page.
 * Returns a Promise (wrapper only — no async I/O).
 * watched_at is NOT set here — popup.js sets it at save time.
 */
function extractVideoInfo() {
  const params = new URLSearchParams(window.location.search);
  const video_id = params.get('v') ?? null;

  const rawTitle = document.title ?? '';
  const suffix = ' - YouTube';
  const video_title = rawTitle.endsWith(suffix)
    ? rawTitle.slice(0, rawTitle.length - suffix.length)
    : rawTitle || null;

  const { channel_name, channel_url } = extractChannelFromInitialData();

  return Promise.resolve({
    video_id,
    video_title,
    channel_name,
    channel_url,
    video_url: window.location.href,
  });
}

// Respond to GET_VIDEO_INFO from popup.js
// IIFE async pattern is more reliable than plain .then() in Safari MV3.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_VIDEO_INFO') {
    (async () => { sendResponse(await extractVideoInfo()); })();
    return true; // keep message channel open for async response
  }
});
```

- [ ] **Step 2: Commit**

```bash
git add safari-extension/content.js
git commit -m "feat: content script — extract video info from ytInitialData"
```

---

## Chunk 3: Popup HTML + CSS

### Task 4: Popup HTML shell

**Files:**
- Create: `safari-extension/popup/popup.html`

- [ ] **Step 1: Create `safari-extension/popup/popup.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>YTArchive</title>
  <link rel="stylesheet" href="popup.css" />
</head>
<body>
  <div id="app"></div>
  <!-- config.js MUST load before popup.js — sets window.CONFIG -->
  <script src="../config.js"></script>
  <script src="popup.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add safari-extension/popup/popup.html
git commit -m "feat: popup html shell"
```

---

### Task 5: Popup CSS — Arctic Ledger design tokens

**Files:**
- Create: `safari-extension/popup/popup.css`

- [ ] **Step 1: Create `safari-extension/popup/popup.css`**

```css
/* safari-extension/popup/popup.css
   Arctic Ledger design system tokens for YTArchive Safari extension */

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #f4f4f7;
  --surface: #ffffff;
  --text: #1a1a2e;
  --text-muted: #6b7280;
  --border: #e5e7eb;
  --sky: #0284c7;
  --sky-hover: #0369a1;
  --mint: #10b981;
  --violet: #7c3aed;
  --violet-light: #ede9fe;
  --red: #ef4444;
  --font: 'DM Sans', system-ui, -apple-system, sans-serif;
  --radius: 6px;
  --radius-sm: 4px;
}

body {
  font-family: var(--font);
  font-size: 13px;
  background: var(--bg);
  color: var(--text);
  width: 300px;
  min-height: 200px;
}

.gradient-strip {
  height: 3px;
  background: linear-gradient(to right, #ef4444, var(--sky), var(--violet));
}

.source-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--border);
}

.source-row .yt-icon { width: 14px; height: 14px; flex-shrink: 0; }

.video-header {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
}

.video-thumb {
  width: 64px;
  height: 36px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  flex-shrink: 0;
  background: var(--border);
}

.video-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }

.video-title {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.video-channel {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.section { padding: 8px 12px; border-bottom: 1px solid var(--border); }

.section-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 5px;
}

.pills { display: flex; flex-wrap: wrap; gap: 4px; }

.pill {
  padding: 3px 8px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  transition: all 0.1s;
  user-select: none;
}

.pill:hover { border-color: var(--sky); color: var(--sky); }
.pill.active { background: var(--sky); border-color: var(--sky); color: white; }
.pill.tag { background: var(--violet-light); border-color: transparent; color: var(--violet); }
.pill.tag:hover { border-color: var(--violet); }
.pill.add-tag { background: transparent; border-style: dashed; color: var(--text-muted); }
.pill.add-tag:hover { border-color: var(--sky); color: var(--sky); }

.tag-dropdown { position: relative; }

.tag-dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 10;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  min-width: 140px;
  max-height: 160px;
  overflow-y: auto;
  padding: 4px 0;
}

.tag-dropdown-item {
  padding: 6px 10px;
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tag-dropdown-item:hover { background: var(--bg); }

.tag-color-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

.notes-textarea {
  width: 100%;
  min-height: 52px;
  resize: vertical;
  font-family: var(--font);
  font-size: 12px;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  margin-top: 6px;
  outline: none;
  transition: border-color 0.15s;
}

.notes-textarea:focus { border-color: var(--sky); }
.notes-textarea::placeholder { color: var(--text-muted); }

.footer {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  gap: 8px;
  border-top: 1px solid var(--border);
}

.footer-left { flex: 1; }

.transcript-link {
  font-size: 11px;
  color: var(--sky);
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
  font-family: var(--font);
}

.transcript-link:hover { text-decoration: underline; }
.transcript-link:disabled { color: var(--text-muted); cursor: not-allowed; pointer-events: none; }

.in-db-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 99px;
  background: var(--mint);
  color: white;
  white-space: nowrap;
}

.btn-save {
  padding: 5px 14px;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: var(--sky);
  color: white;
  transition: background 0.15s;
  white-space: nowrap;
}

.btn-save:hover { background: var(--sky-hover); }
.btn-save:disabled { background: var(--border); color: var(--text-muted); cursor: not-allowed; }

.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  vertical-align: middle;
  margin-right: 4px;
}

@keyframes spin { to { transform: rotate(360deg); } }

.shimmer {
  background: linear-gradient(90deg, var(--border) 25%, #f0f0f4 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: shimmer-anim 1.2s infinite;
  border-radius: var(--radius-sm);
}

@keyframes shimmer-anim { to { background-position: -200% 0; } }

.shimmer-title { height: 12px; width: 85%; margin-bottom: 4px; }
.shimmer-channel { height: 10px; width: 55%; }
.shimmer-thumb { width: 64px; height: 36px; flex-shrink: 0; border-radius: var(--radius-sm); }

.error-banner {
  padding: 8px 12px;
  background: #fef2f2;
  border-top: 1px solid #fecaca;
  font-size: 11px;
  color: var(--red);
}

.pending-banner {
  padding: 6px 12px;
  background: #fffbeb;
  border-bottom: 1px solid #fde68a;
  font-size: 11px;
  color: #92400e;
}

.not-video-state {
  padding: 32px 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}

.btn-offline {
  margin-top: 6px;
  padding: 4px 10px;
  font-size: 11px;
  font-family: var(--font);
  font-weight: 500;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text);
}

.btn-offline:hover { border-color: var(--sky); color: var(--sky); }
```

- [ ] **Step 2: Commit**

```bash
git add safari-extension/popup/popup.css
git commit -m "feat: popup css — arctic ledger tokens and layout"
```

---

## Chunk 4: Popup JS

### Task 6: Popup state machine and API client

**Files:**
- Create: `safari-extension/popup/popup.js`

**Security:** All user data is sanitized with `escHtml()` before DOM insertion via `textContent` where possible, and via the escaping utility when building HTML strings. Raw API data is never inserted unsanitized.

- [ ] **Step 1: Create `safari-extension/popup/popup.js`**

```js
// safari-extension/popup/popup.js
// Classic script (no import/export). CONFIG is available from config.js.
//
// State machine phases:
//   loading -> new_video | already_saved | not_video | error
//   new_video | already_saved -> saving -> success (auto-close) | error
//   error -> retry save | save_offline

// ── Utility ─────────────────────────────────────────────────────────────────

/** Escape HTML entities to prevent XSS when building HTML strings. */
function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ── State ────────────────────────────────────────────────────────────────────

const state = {
  phase: 'loading',       // loading | not_video | new_video | already_saved | saving | error
  videoInfo: null,        // { video_id, video_title, channel_name, channel_url, video_url }
  existingVideo: null,    // full response from GET /api/videos/{id}, or null
  allTags: [],            // [{ id, name, color }] from GET /api/tags
  tagsError: false,
  selectedTags: [],       // [string] tag names
  selectedStatus: null,   // watchlist_status string or null
  notes: '',
  errorMsg: '',
  transcriptMsg: '',      // '' | 'fetching' | 'done' | 'error'
  pendingQueue: [],       // from chrome.storage.local
};

// ── API helpers ──────────────────────────────────────────────────────────────

const BASE = CONFIG.API_BASE_URL;

async function apiFetch(path, options) {
  const opts = options || {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const res = await fetch(BASE + path, Object.assign({}, opts, {
      signal: controller.signal,
      headers: Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {}),
    }));
    clearTimeout(timer);
    return res;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

// ── Offline queue ────────────────────────────────────────────────────────────

function loadQueue() {
  return new Promise(function(resolve) {
    chrome.storage.local.get(['pendingQueue'], function(result) {
      resolve(result.pendingQueue || []);
    });
  });
}

function saveQueue(queue) {
  return new Promise(function(resolve) {
    chrome.storage.local.set({ pendingQueue: queue }, resolve);
  });
}

async function flushQueue(queue) {
  const remaining = queue.slice();
  let i = 0;
  while (i < remaining.length) {
    const item = remaining[i];
    try {
      const res = await apiFetch('/api/videos', {
        method: 'POST',
        body: JSON.stringify(item.payload),
      });
      if (res.ok) {
        remaining.splice(i, 1);
        await saveQueue(remaining);
        // don't increment i — next item slides into position i
      } else if (res.status >= 400 && res.status < 500) {
        console.warn('[YTArchive] Dropping unrecoverable queue item (4xx):', res.status, item);
        remaining.splice(i, 1);
        await saveQueue(remaining);
      } else {
        // 5xx — move to tail, stop flush
        remaining.splice(i, 1);
        item.retryCount = (item.retryCount || 0) + 1;
        if (item.retryCount < 3) remaining.push(item);
        else console.warn('[YTArchive] Dropping item after 3 retries (5xx):', item);
        await saveQueue(remaining);
        break;
      }
    } catch (_err) {
      // Network error — move to tail, stop flush
      remaining.splice(i, 1);
      item.retryCount = (item.retryCount || 0) + 1;
      if (item.retryCount < 3) remaining.push(item);
      else console.warn('[YTArchive] Dropping item after 3 retries (network):', item);
      await saveQueue(remaining);
      break;
    }
  }
  return remaining;
}

// ── Build POST payload ───────────────────────────────────────────────────────

function buildPayload() {
  const v = state.videoInfo;
  const payload = {
    video_id: v.video_id,
    video_title: v.video_title,
    video_url: v.video_url,
    channel_name: v.channel_name,
    channel_url: v.channel_url,
    watched_at: new Date().toISOString(),
    tags: state.selectedTags.slice(),
    fetch_transcript: false,
  };
  if (state.selectedStatus) payload.watchlist_status = state.selectedStatus;
  if (state.notes.trim()) payload.notes = state.notes.trim();
  return payload;
}

// ── Save ─────────────────────────────────────────────────────────────────────

async function handleSave() {
  state.phase = 'saving';
  render();

  const hadStatus = state.existingVideo && state.existingVideo.watchlist
    ? state.existingVideo.watchlist.status
    : null;
  const clearingStatus = !!hadStatus && !state.selectedStatus;

  try {
    const res = await apiFetch('/api/videos', {
      method: 'POST',
      body: JSON.stringify(buildPayload()),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);

    // Separately clear watchlist if user deselected all pills on an already-saved video.
    // POST /api/videos cannot clear watchlist_status (backend ignores null/missing value).
    if (clearingStatus) {
      try {
        await apiFetch('/api/watchlist/' + state.videoInfo.video_id, { method: 'DELETE' });
      } catch (_e) {
        console.warn('[YTArchive] Could not clear watchlist status');
      }
    }

    window.close();
  } catch (_err) {
    state.phase = 'error';
    state.errorMsg = 'Could not save. Is the server running?';
    render();
  }
}

async function handleSaveOffline() {
  const queue = await loadQueue();
  queue.push({ payload: buildPayload(), retryCount: 0 });
  await saveQueue(queue); // write before close
  state.errorMsg = 'Saved locally — open popup when your server is running to sync.';
  render();
  setTimeout(function() { window.close(); }, 2000);
}

// ── Transcript ───────────────────────────────────────────────────────────────

async function handleFetchTranscript() {
  state.transcriptMsg = 'fetching';
  render();
  try {
    const res = await apiFetch('/api/transcripts/' + state.videoInfo.video_id + '/fetch', {
      method: 'POST',
    });
    state.transcriptMsg = (res.ok || res.status === 202) ? 'done' : 'error';
  } catch (_err) {
    state.transcriptMsg = 'error';
  }
  render();
  const delay = state.transcriptMsg === 'error' ? 2000 : 1500;
  setTimeout(function() { state.transcriptMsg = ''; render(); }, delay);
}

// ── DOM helpers (safe — use textContent for untrusted values) ─────────────────

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  if (attrs) {
    Object.keys(attrs).forEach(function(k) {
      if (k === 'class') node.className = attrs[k];
      else if (k === 'style') node.style.cssText = attrs[k];
      else if (k === 'disabled') { if (attrs[k]) node.disabled = true; }
      else node.setAttribute(k, attrs[k]);
    });
  }
  if (children) {
    (Array.isArray(children) ? children : [children]).forEach(function(child) {
      if (child == null) return;
      if (typeof child === 'string') node.appendChild(document.createTextNode(child));
      else node.appendChild(child);
    });
  }
  return node;
}

// ── Render ───────────────────────────────────────────────────────────────────

function render() {
  const app = document.getElementById('app');
  // Clear existing content
  while (app.firstChild) app.removeChild(app.firstChild);
  buildUI(app);
  attachListeners();
}

function buildUI(app) {
  // Gradient strip
  app.appendChild(el('div', { class: 'gradient-strip' }));

  // Source row
  const ytSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  ytSvg.setAttribute('viewBox', '0 0 24 24');
  ytSvg.setAttribute('class', 'yt-icon');
  ytSvg.setAttribute('fill', '#ef4444');
  const ytPath1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  ytPath1.setAttribute('d', 'M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2C0 8.1 0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1C24 15.9 24 12 24 12s0-3.9-.5-5.8z');
  const ytPath2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  ytPath2.setAttribute('d', 'M9.6 15.6V8.4l6.3 3.6-6.3 3.6z');
  ytPath2.setAttribute('fill', 'white');
  ytSvg.appendChild(ytPath1);
  ytSvg.appendChild(ytPath2);
  app.appendChild(el('div', { class: 'source-row' }, [ytSvg, 'YouTube']));

  const { phase } = state;

  if (phase === 'loading') { buildLoadingUI(app); return; }
  if (phase === 'not_video') { buildNotVideoUI(app); return; }

  // Pending banner
  if (state.pendingQueue.length > 0) {
    const count = state.pendingQueue.length;
    app.appendChild(el('div', { class: 'pending-banner' },
      '\u23F3 ' + count + ' item' + (count > 1 ? 's' : '') + ' pending sync'));
  }

  buildVideoUI(app);
}

function buildLoadingUI(app) {
  const header = el('div', { class: 'video-header' }, [
    el('div', { class: 'shimmer shimmer-thumb' }),
    el('div', { class: 'video-meta' }, [
      el('div', { class: 'shimmer shimmer-title' }),
      el('div', { class: 'shimmer shimmer-channel' }),
    ]),
  ]);
  app.appendChild(header);
  app.appendChild(el('div', { class: 'section' }, [el('div', { class: 'shimmer', style: 'height:22px;width:100%' })]));
  app.appendChild(el('div', { class: 'section' }, [el('div', { class: 'shimmer', style: 'height:22px;width:70%' })]));
}

function buildNotVideoUI(app) {
  app.appendChild(el('div', { class: 'not-video-state' }, 'Open a YouTube video to use this extension.'));
}

function buildVideoUI(app) {
  const { videoInfo, existingVideo, allTags, selectedTags, selectedStatus,
          notes, phase, errorMsg, transcriptMsg, tagsError } = state;

  const isAlreadySaved = !!existingVideo;
  const hasTranscript = !!(existingVideo && existingVideo.transcript);
  const isSaving = phase === 'saving';
  const isError = phase === 'error';

  // Video header
  const thumbImg = el('img', {
    class: 'video-thumb',
    src: 'https://img.youtube.com/vi/' + videoInfo.video_id + '/hqdefault.jpg',
    alt: '',
  });
  const titleEl = el('div', { class: 'video-title' });
  titleEl.textContent = videoInfo.video_title || 'Untitled';
  const metaChildren = [titleEl];
  if (videoInfo.channel_name) {
    const channelEl = el('div', { class: 'video-channel' });
    channelEl.textContent = videoInfo.channel_name;
    metaChildren.push(channelEl);
  }
  app.appendChild(el('div', { class: 'video-header' }, [
    thumbImg,
    el('div', { class: 'video-meta' }, metaChildren),
  ]));

  // Status pills
  const statusOptions = [
    { label: 'to-rewatch', value: 'to-rewatch' },
    { label: 'reference',  value: 'reference' },
    { label: 'download',   value: 'to-download' },
    { label: 'done',       value: 'done' },
  ];
  const pillEls = statusOptions.map(function(opt) {
    const active = selectedStatus === opt.value;
    const btn = el('button', { class: 'pill' + (active ? ' active' : ''), 'data-status': opt.value });
    btn.textContent = opt.label;
    return btn;
  });
  app.appendChild(el('div', { class: 'section' }, [el('div', { class: 'pills' }, pillEls)]));

  // Tags section
  const tagPillEls = selectedTags.map(function(name) {
    const btn = el('button', { class: 'pill tag', 'data-remove-tag': name });
    btn.textContent = name + ' \u00D7';
    return btn;
  });

  const availableTags = allTags.filter(function(t) { return !selectedTags.includes(t.name); });
  const dropdownItems = availableTags.map(function(t) {
    const dot = el('span', { class: 'tag-color-dot', style: 'background:' + (t.color || '#7c3aed') });
    const item = el('div', { class: 'tag-dropdown-item', 'data-add-tag': t.name }, [dot]);
    const nameSpan = document.createTextNode(t.name);
    item.appendChild(nameSpan);
    return item;
  });

  const tagPillsContainer = el('div', { class: 'pills' }, tagPillEls);

  if (availableTags.length > 0) {
    const dropdownMenu = el('div', { class: 'tag-dropdown-menu', id: 'tag-dropdown', style: 'display:none' }, dropdownItems);
    const addBtn = el('button', { class: 'pill add-tag', id: 'add-tag-btn' }, '+ add \u25BE');
    const wrapper = el('div', { class: 'tag-dropdown' }, [addBtn, dropdownMenu]);
    tagPillsContainer.appendChild(wrapper);
  }

  if (tagsError && allTags.length === 0) {
    const errSpan = el('span', { style: 'font-size:10px;color:var(--text-muted)' }, 'Tags unavailable');
    tagPillsContainer.appendChild(errSpan);
  }

  app.appendChild(el('div', { class: 'section' }, [
    el('div', { class: 'section-label' }, 'Tags'),
    tagPillsContainer,
  ]));

  // Notes
  const textarea = el('textarea', {
    class: 'notes-textarea',
    id: 'notes-input',
    placeholder: 'Add a note\u2026',
  });
  textarea.value = notes;
  app.appendChild(el('div', { class: 'section' }, [
    el('div', { class: 'section-label' }, 'Notes'),
    textarea,
  ]));

  // Error banner
  if (isError) {
    const errMsg = el('span');
    errMsg.textContent = errorMsg;
    const offlineBtn = el('button', { class: 'btn-offline', id: 'save-offline-btn' }, 'Save Offline');
    const banner = el('div', { class: 'error-banner' }, [errMsg, el('div', {}, [offlineBtn])]);
    app.appendChild(banner);
  }

  // Footer
  const transcriptLabel = hasTranscript ? 'Re-fetch Transcript' : 'Fetch Transcript';
  const transcriptDisplay = transcriptMsg === 'fetching' ? 'Fetching\u2026'
    : transcriptMsg === 'error' ? 'Transcript unavailable'
    : transcriptMsg === 'done' ? 'Queued!'
    : transcriptLabel;

  const transcriptDisabled = !isAlreadySaved || isSaving;
  const transcriptBtn = el('button', {
    class: 'transcript-link',
    id: 'fetch-transcript-btn',
    disabled: transcriptDisabled,
  });
  transcriptBtn.textContent = transcriptDisplay;

  const footerLeft = el('div', { class: 'footer-left' }, [transcriptBtn]);

  const footerChildren = [footerLeft];

  if (isAlreadySaved) {
    footerChildren.push(el('span', { class: 'in-db-badge' }, '\u25CF In DB'));
  }

  const saveBtn = el('button', {
    class: 'btn-save',
    id: 'save-btn',
    disabled: isSaving,
  });
  if (isSaving) {
    const spinner = el('span', { class: 'spinner' });
    saveBtn.appendChild(spinner);
    saveBtn.appendChild(document.createTextNode(isAlreadySaved ? 'Updating\u2026' : 'Saving\u2026'));
  } else {
    saveBtn.textContent = isAlreadySaved ? 'Update' : 'Save to Archive';
  }
  footerChildren.push(saveBtn);

  app.appendChild(el('div', { class: 'footer' }, footerChildren));
}

// ── Event listeners ──────────────────────────────────────────────────────────

function attachListeners() {
  const saveBtn = document.getElementById('save-btn');
  if (saveBtn) saveBtn.addEventListener('click', handleSave);

  const offlineBtn = document.getElementById('save-offline-btn');
  if (offlineBtn) offlineBtn.addEventListener('click', handleSaveOffline);

  const transcriptBtn = document.getElementById('fetch-transcript-btn');
  if (transcriptBtn) transcriptBtn.addEventListener('click', handleFetchTranscript);

  const notesInput = document.getElementById('notes-input');
  if (notesInput) notesInput.addEventListener('input', function(e) { state.notes = e.target.value; });

  // Status pills
  document.querySelectorAll('[data-status]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      const v = btn.getAttribute('data-status');
      state.selectedStatus = state.selectedStatus === v ? null : v;
      render();
    });
  });

  // Tag removal
  document.querySelectorAll('[data-remove-tag]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      const name = btn.getAttribute('data-remove-tag');
      state.selectedTags = state.selectedTags.filter(function(t) { return t !== name; });
      render();
    });
  });

  // Tag add dropdown toggle
  const addTagBtn = document.getElementById('add-tag-btn');
  const tagDropdown = document.getElementById('tag-dropdown');
  if (addTagBtn && tagDropdown) {
    addTagBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      tagDropdown.style.display = tagDropdown.style.display === 'none' ? 'block' : 'none';
    });
  }

  // Tag selection
  document.querySelectorAll('[data-add-tag]').forEach(function(item) {
    item.addEventListener('click', function() {
      const name = item.getAttribute('data-add-tag');
      if (name && !state.selectedTags.includes(name)) {
        state.selectedTags = state.selectedTags.concat([name]);
      }
      render();
    });
  });

  // Close dropdown on outside click
  document.addEventListener('click', function() {
    const dd = document.getElementById('tag-dropdown');
    if (dd) dd.style.display = 'none';
  }, { once: true });
}

// ── Init ─────────────────────────────────────────────────────────────────────

async function init() {
  state.phase = 'loading';
  render();

  // Flush any offline queue before rendering current video
  const queue = await loadQueue();
  if (queue.length > 0) {
    state.pendingQueue = await flushQueue(queue);
    render();
  }

  // Get active tab and query content script
  let videoInfo;
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const tab = tabs[0];
    videoInfo = await chrome.tabs.sendMessage(tab.id, { type: 'GET_VIDEO_INFO' });
  } catch (_err) {
    state.phase = 'error';
    state.errorMsg = "Couldn't reach the page. Try reloading YouTube.";
    render();
    return;
  }

  state.videoInfo = videoInfo;

  if (!videoInfo || !videoInfo.video_id) {
    state.phase = 'not_video';
    render();
    return;
  }

  // Load video + tags in parallel
  const videoPromise = apiFetch('/api/videos/' + videoInfo.video_id)
    .then(function(r) { return r.status === 404 ? null : r.json(); })
    .catch(function() { return null; });

  const tagsPromise = apiFetch('/api/tags')
    .then(function(r) { return r.ok ? r.json() : []; })
    .catch(function() { state.tagsError = true; return []; });

  const results = await Promise.all([videoPromise, tagsPromise]);
  const existingVideo = results[0];
  const allTags = results[1];

  state.existingVideo = existingVideo;
  state.allTags = allTags;

  if (existingVideo) {
    state.selectedTags = (existingVideo.tags || []).map(function(t) { return t.name; });
    state.selectedStatus = (existingVideo.watchlist && existingVideo.watchlist.status)
      ? existingVideo.watchlist.status : null;
    state.notes = existingVideo.notes || '';
    state.phase = 'already_saved';
  } else {
    state.phase = 'new_video';
  }

  render();
}

document.addEventListener('DOMContentLoaded', init);
```

- [ ] **Step 2: Commit**

```bash
git add safari-extension/popup/popup.js
git commit -m "feat: popup js — state machine, api client, offline queue, dom render"
```

---

## Chunk 5: Xcode Wrapping + Manual Testing

### Task 7: Wrap for Safari and verify end-to-end

**Files:**
- No new files — wraps the extension in Xcode and validates manually

- [ ] **Step 1: Run the Xcode converter**

From the project root:

```bash
xcrun safari-web-extension-converter "safari-extension/" \
  --project-location . \
  --app-name YTArchive \
  --macos-only
```

Expected output ends with: `Generated Xcode project at: ./YTArchive/YTArchive.xcodeproj`

If you see `xcrun: error: unable to find utility`:
```bash
xcode-select --install
```

- [ ] **Step 2: Build in Xcode**

```bash
open YTArchive/YTArchive.xcodeproj
```

Select the `YTArchive` scheme → ⌘R. A blank app window appears — that's expected.

- [ ] **Step 3: Enable in Safari**

Safari → Settings → Extensions → ✓ YTArchive → Always Allow on youtube.com

- [ ] **Step 4: Test — not-a-video state**

1. Navigate to `youtube.com` homepage
2. Click extension icon
3. Expected: "Open a YouTube video to use this extension."

- [ ] **Step 5: Test — new video save**

1. Navigate to any YouTube video (e.g., `youtube.com/watch?v=dQw4w9WgXcQ`)
2. Badge shows green `●` in toolbar
3. Click icon → shimmer briefly → title/channel/thumbnail appear
4. Select a status pill, pick a tag, add a note
5. Click **Save to Archive**
6. Expected: popup closes
7. Verify at `http://localhost:8000` that the video appears

- [ ] **Step 6: Test — already saved pre-fill**

1. Click icon on the same video again
2. Expected: form pre-filled with your tags/status/notes, "● In DB" badge, button says "Update"

- [ ] **Step 7: Test — status clearing**

1. Open popup on a saved video that has a status set
2. Click the active status pill to deselect it (no pill highlighted)
3. Click **Update**
4. Expected: popup closes; re-open and verify "● In DB" badge present but no status pill highlighted

- [ ] **Step 8: Test — Fetch Transcript**

1. Navigate to a video not yet saved → "Fetch Transcript" link is grey/disabled
2. Save it → popup closes
3. Re-open popup on same video → link is enabled
4. Click it → "Fetching…" for ~1.5s, then reverts to label

- [ ] **Step 9: Test — offline queue**

1. Stop the backend (`Ctrl+C` on uvicorn)
2. Navigate to a new YouTube video and open popup
3. Try to save → error banner + "Save Offline" button appear
4. Click Save Offline → confirmation, popup closes
5. Restart backend
6. Open popup on any video → "1 item pending sync" notice appears, syncs
7. Verify the offline-saved video now appears in the web UI

- [ ] **Step 10: Commit Xcode project**

```bash
git add YTArchive/
git commit -m "feat: xcode wrapper for ytarchive safari extension"
```

---

## Chunk 6: Backend — DELETE /watchlist endpoint

### Task 8: Verify and add DELETE /api/watchlist/{video_id}

**Files:**
- Read: `backend/routers/watchlist.py`

The extension calls `DELETE /api/watchlist/{video_id}` when the user clears watchlist status. Verify this endpoint exists.

- [ ] **Step 1: Check for the DELETE watchlist endpoint across all backend routers**

```bash
grep -rn "DELETE\|delete.*watchlist\|watchlist.*delete" backend/routers/
```

Expected: a line like `@router.delete("/watchlist/{video_id}")` in one of the router files.
If found, run Step 3 (the curl test) to verify it works correctly before skipping Step 2.

- [ ] **Step 2: If endpoint is missing, add it to `backend/routers/watchlist.py`**

Open `backend/routers/watchlist.py` and add after existing routes:

```python
@router.delete("/watchlist/{video_id}", status_code=204)
async def remove_from_watchlist(
    video_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    await db.execute("DELETE FROM watchlist WHERE video_id = ?", [video_id])
    await db.commit()
```

- [ ] **Step 3: Verify the endpoint manually**

```bash
# Save a video with a watchlist status
curl -s -X POST http://localhost:8000/api/videos \
  -H 'Content-Type: application/json' \
  -d '{"video_id":"test-del-123","video_title":"Delete Test","video_url":"https://youtube.com/watch?v=test-del-123","watched_at":"2026-03-21T12:00:00Z","tags":[],"watchlist_status":"reference","fetch_transcript":false}' \
  | python3 -m json.tool | grep -A2 watchlist

# Remove it
curl -s -o /dev/null -w "%{http_code}" -X DELETE http://localhost:8000/api/watchlist/test-del-123
# Expected: 204

# Confirm it's gone
curl -s http://localhost:8000/api/videos/test-del-123 | python3 -m json.tool | grep watchlist
# Expected: "watchlist": null
```

- [ ] **Step 4: Commit if the endpoint was added**

```bash
git add backend/routers/watchlist.py
git commit -m "feat: add DELETE /watchlist/{video_id} endpoint"
```

---

## Reload Cheatsheet

| Change type | Action |
|---|---|
| Edit any JS/HTML/CSS | Safari → Settings → Extensions → toggle YTArchive off/on |
| Edit manifest.json or add a new file | Re-run `xcrun safari-web-extension-converter`, rebuild in Xcode (⌘R), re-enable |
