# Frontend Thumbnails Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display YouTube video thumbnails in the Library list rows and the VideoDetail panel using YouTube's public CDN — no backend changes required.

**Architecture:** Thumbnail URLs are derived client-side from `video_id` using `https://img.youtube.com/vi/{video_id}/hqdefault.jpg`. In the list view, the thumbnail replaces the channel-initial badge. In the detail panel, a hero thumbnail is inserted between the sticky header and the watch history section. Both use an `onError` handler to degrade gracefully when a thumbnail is unavailable.

**Tech Stack:** React 18, TailwindCSS 4 (Arctic Ledger design tokens), no new dependencies.

---

## Chunk 1: List view thumbnail

### Task 1: Replace channel-initial badge with thumbnail in VideoRow

**Files:**
- Modify: `frontend/src/pages/Library.jsx` (VideoRow component, lines 219–278)

**Context:**
The `VideoRow` component currently renders a `w-9 h-9` channel-initial badge:
```jsx
<div className="w-9 h-9 rounded-lg bg-accent-sky-dim flex items-center justify-center shrink-0">
  <span className="text-sm font-semibold text-accent-sky font-mono">
    {(video.channel_name ?? '?')[0].toUpperCase()}
  </span>
</div>
```

Replace it with an `<img>` that shows the YouTube thumbnail and falls back to the channel-initial div on error. The fallback must use a React `useState` flag — setting `img.src` in `onError` can cause infinite loops if the fallback URL also fails.

- [ ] **Step 1: Add useState import** (it is already imported via React — confirm at top of Library.jsx)

The file already uses hooks via `useState`. No import change needed.

- [ ] **Step 2: Add a VideoThumb helper component** just above the `VideoRow` function definition (around line 219):

```jsx
function VideoThumb({ videoId, channelName }) {
  const [errored, setErrored] = useState(false)
  if (errored || !videoId) {
    return (
      <div className="w-16 h-9 rounded-md bg-accent-sky-dim flex items-center justify-center shrink-0">
        <span className="text-sm font-semibold text-accent-sky font-mono">
          {(channelName ?? '?')[0].toUpperCase()}
        </span>
      </div>
    )
  }
  return (
    <img
      src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
      alt=""
      onError={() => setErrored(true)}
      className="w-16 h-9 rounded-md object-cover shrink-0 bg-surface-2"
    />
  )
}
```

Note: width changed from `w-9 h-9` (square) to `w-16 h-9` (16:9) to match thumbnail aspect ratio.

- [ ] **Step 3: Replace the channel-initial div in VideoRow** with `<VideoThumb>`:

Replace:
```jsx
      {/* Channel initial */}
      <div className="w-9 h-9 rounded-lg bg-accent-sky-dim flex items-center justify-center shrink-0">
        <span className="text-sm font-semibold text-accent-sky font-mono">
          {(video.channel_name ?? '?')[0].toUpperCase()}
        </span>
      </div>
```

With:
```jsx
      {/* Thumbnail */}
      <VideoThumb videoId={video.video_id} channelName={video.channel_name} />
```

- [ ] **Step 4: Verify in browser**

- Open the frontend (`npm run dev` in `frontend/`).
- Navigate to the Library page.
- Confirm thumbnail images appear in each row.
- Confirm the row height is unchanged (thumbnails fit inline).
- Disconnect from the internet or use a fake video_id to confirm the channel-initial fallback renders correctly.

---

## Chunk 2: Detail panel hero thumbnail

### Task 2: Add hero thumbnail to VideoDetail panel

**Files:**
- Modify: `frontend/src/components/VideoDetail.jsx` (after sticky header, around line 160)

**Context:**
The panel body begins after the sticky header closing tag at line ~160. The first section after that is watch history. Insert a hero thumbnail block between the header and the first section.

The detail panel is `max-w-lg` wide (~512px). A 16:9 thumbnail at full panel width renders at ~512×288px, which is well within `hqdefault` quality (480×360).

- [ ] **Step 1: Add hero thumbnail block** inside the body `<div className="p-5 space-y-6">` (line 161), within the non-loading `<>` branch (line 169), immediately before the `{/* Watch history */}` section (line 170). This ensures the thumbnail only renders when `video` data is available and inherits the consistent body padding:

```jsx
              {/* Hero thumbnail */}
              {video?.video_id && <HeroThumb videoId={video.video_id} />}

              {/* Watch history */}
```

- [ ] **Step 2: Add the HeroThumb helper component** near the top of the file, just before the `export default function VideoDetail` line:

```jsx
function HeroThumb({ videoId }) {
  const [errored, setErrored] = useState(false)
  if (errored) return null
  return (
    <img
      src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
      alt=""
      onError={() => setErrored(true)}
      className="w-full rounded-lg object-cover bg-surface-2"
      style={{ aspectRatio: '16/9' }}
    />
  )
}
```

Note: `HeroThumb` returns `null` on error (no fallback needed — the header already shows the title and channel). `useState` is already imported at the top of `VideoDetail.jsx`.

- [ ] **Step 3: Verify in browser**

- Click any video in the Library.
- Confirm the hero thumbnail appears below the sticky header.
- Confirm the thumbnail scales to panel width with correct aspect ratio.
- Confirm scrolling works normally (thumbnail scrolls with content, not sticky).
- Use a fake video_id to confirm the component renders `null` gracefully without layout shift.
