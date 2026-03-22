const BASE = '/api'

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  if (res.status === 204) return null
  return res.json()
}

// ── Videos ──────────────────────────────────────────────────────────

export function fetchVideos(params) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') qs.set(k, v)
  })
  return req(`/videos?${qs}`)
}

export function fetchVideo(videoId) {
  return req(`/videos/${videoId}`)
}

export function addVideo(body) {
  return req('/videos', { method: 'POST', body })
}

// ── Tags ─────────────────────────────────────────────────────────────

export function fetchTags() {
  return req('/tags')
}

export function createTag(body) {
  return req('/tags', { method: 'POST', body })
}

export function updateTag(tagId, body) {
  return req(`/tags/${tagId}`, { method: 'PATCH', body })
}

export function deleteTag(tagId) {
  return req(`/tags/${tagId}`, { method: 'DELETE' })
}

export function setVideoTags(videoId, tagIds) {
  return req(`/videos/${videoId}/tags`, { method: 'PUT', body: { tag_ids: tagIds } })
}

export function addVideoTag(videoId, tagId) {
  return req(`/videos/${videoId}/tags/${tagId}`, { method: 'POST' })
}

export function removeVideoTag(videoId, tagId) {
  return req(`/videos/${videoId}/tags/${tagId}`, { method: 'DELETE' })
}

// ── Watchlist ────────────────────────────────────────────────────────

export function fetchWatchlist(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, v) })
  return req(`/watchlist?${qs}`)
}

export function addToWatchlist(body) {
  return req('/watchlist', { method: 'POST', body })
}

export function updateWatchlistItem(videoId, body) {
  return req(`/watchlist/${videoId}`, { method: 'PATCH', body })
}

export function removeFromWatchlist(videoId) {
  return req(`/watchlist/${videoId}`, { method: 'DELETE' })
}

// ── Transcripts ──────────────────────────────────────────────────────

export function fetchTranscript(videoId) {
  return req(`/transcripts/${videoId}`)
}

export function triggerTranscriptFetch(videoId) {
  return req(`/transcripts/${videoId}/fetch`, { method: 'POST' })
}

export function fetchTranscriptObsidian(videoId) {
  return fetch(`${BASE}/transcripts/${videoId}/obsidian`).then(r => r.text())
}

// ── Notes ────────────────────────────────────────────────────────────

export function fetchNotes(videoId) {
  return req(`/videos/${videoId}/notes`)
}

export function upsertNotes(videoId, content) {
  return req(`/videos/${videoId}/notes`, { method: 'PUT', body: { content } })
}

// ── Stats ─────────────────────────────────────────────────────────────

export function fetchStats() {
  return req('/stats')
}
