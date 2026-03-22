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
    channel_name: v.channel_name || null,
    channel_url: v.channel_url || null,
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
      const delRes = await apiFetch('/api/watchlist/' + state.videoInfo.video_id, { method: 'DELETE' })
        .catch(function() { return null; });
      if (!delRes || (!delRes.ok && delRes.status !== 404)) {
        // Watchlist clear failed — surface to user rather than silently losing their intent
        state.phase = 'error';
        state.errorMsg = 'Saved, but could not clear watchlist status. Try again.';
        render();
        return;
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

  // New tag input — always rendered so user can create tags even when all existing tags are selected
  const newTagInput = el('input', {
    type: 'text',
    id: 'new-tag-input',
    class: 'new-tag-input',
    placeholder: 'New tag\u2026',
  });
  tagPillsContainer.appendChild(newTagInput);

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

  // New tag creation
  const newTagInputEl = document.getElementById('new-tag-input');
  if (newTagInputEl) {
    // Prevent outside-click handler from closing the dropdown when user clicks the input
    newTagInputEl.addEventListener('click', function(e) { e.stopPropagation(); });

    var creatingTag = false;
    newTagInputEl.addEventListener('keydown', function(e) {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      e.stopPropagation();
      const name = newTagInputEl.value.trim();
      if (!name) return;
      if (creatingTag) return; // prevent double-submit

      // If a tag with this name already exists, just select it without an API call
      const existing = state.allTags.find(function(t) { return t.name.toLowerCase() === name.toLowerCase(); });
      if (existing) {
        if (!state.selectedTags.includes(existing.name)) {
          state.selectedTags = state.selectedTags.concat([existing.name]);
        }
        render();
        return;
      }

      function showError() {
        const inputEl = document.getElementById('new-tag-input');
        if (inputEl) {
          inputEl.placeholder = 'Error \u2014 try again';
          setTimeout(function() {
            const resetEl = document.getElementById('new-tag-input');
            if (resetEl) resetEl.placeholder = 'New tag\u2026';
          }, 2000);
        }
      }

      creatingTag = true;
      (async function() {
        try {
          const res = await apiFetch('/api/tags', {
            method: 'POST',
            body: JSON.stringify({ name: name }),
          });
          if (res.ok) {
            const tag = await res.json();
            if (!tag || typeof tag.name !== 'string') { showError(); return; }
            state.allTags = state.allTags.concat([tag]);
            state.selectedTags = state.selectedTags.concat([tag.name]);
            render();
          } else {
            showError();
          }
        } catch (_err) {
          showError();
        } finally {
          creatingTag = false;
        }
      })();
    });
  }

  // Close dropdown on outside click.
  // Use a module-level flag so this listener is registered only once per popup lifetime,
  // not on every render() call (attaching { once: true } on every render accumulates stale handlers).
  if (!attachListeners._dropdownListenerAdded) {
    attachListeners._dropdownListenerAdded = true;
    document.addEventListener('click', function handler() {
      const dd = document.getElementById('tag-dropdown');
      if (dd) dd.style.display = 'none';
    });
  }
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
    const tab = tabs && tabs[0];
    if (!tab) {
      state.phase = 'not_video';
      render();
      return;
    }
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
  state.allTags = Array.isArray(allTags) ? allTags : [];

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
