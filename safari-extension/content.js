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

  const rawTitle = document.title;
  const suffix = ' - YouTube';
  const stripped = rawTitle.endsWith(suffix)
    ? rawTitle.slice(0, rawTitle.length - suffix.length)
    : rawTitle;
  const video_title = stripped || null;

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
