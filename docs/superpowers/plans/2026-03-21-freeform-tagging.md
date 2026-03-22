# Free-Form Tagging Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users create new tags on the fly by typing a name and pressing Enter — in both the web client tag picker and the Safari extension popup.

**Architecture:** Three independent changes: (1) add a 409 guard to the backend `POST /api/tags` handler so duplicate names return a proper HTTP error instead of a 500; (2) add a text input with a `useMutation` to `TagPicker.jsx`; (3) add a text input to the Safari popup's tag section and wire it in `attachListeners`. No new files, no new API endpoints.

**Tech Stack:** Python/FastAPI/aiosqlite (backend), React 18 + React Query v5 + TailwindCSS 4 (web), plain JS + DOM helpers (Safari extension).

**Note:** There is no git repository in this project — skip all git commit steps.

---

## Chunk 1: Backend duplicate-name guard

### Task 1: Return 409 on duplicate tag name

**Files:**
- Modify: `backend/routers/tags.py` (lines 28–34, `create_tag` handler)

**Context:**
The `tags` table has `UNIQUE` on `name`. A bare `INSERT` on a duplicate raises `aiosqlite.IntegrityError`, which FastAPI converts to a 500. We need a 409 instead so the clients can differentiate duplicate-name errors from genuine failures.

Current handler (lines 28–34):
```python
@router.post("/tags", response_model=TagOut, status_code=201)
async def create_tag(body: TagCreate, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute(
        "INSERT INTO tags (name, color) VALUES (?, ?)", [body.name, body.color]
    ) as cursor:
        tag_id = cursor.lastrowid
    await db.commit()
    return TagOut(id=tag_id, name=body.name, color=body.color, video_count=0)
```

- [ ] **Step 1: Replace the `create_tag` handler body** with a try/except that catches `aiosqlite.IntegrityError`:

```python
@router.post("/tags", response_model=TagOut, status_code=201)
async def create_tag(body: TagCreate, db: aiosqlite.Connection = Depends(get_db)):
    try:
        async with db.execute(
            "INSERT INTO tags (name, color) VALUES (?, ?)", [body.name, body.color]
        ) as cursor:
            tag_id = cursor.lastrowid
        await db.commit()
    except aiosqlite.IntegrityError:
        raise HTTPException(status_code=409, detail="Tag name already exists")
    return TagOut(id=tag_id, name=body.name, color=body.color, video_count=0)
```

- [ ] **Step 2: Verify the server is running and test both paths**

With the backend running (`uvicorn main:app --reload` in `backend/`):

Create a new tag:
```bash
curl -s -X POST http://localhost:8000/api/tags \
  -H "Content-Type: application/json" \
  -d '{"name":"test-freeform"}' | python3 -m json.tool
```
Expected: `{"id": <n>, "name": "test-freeform", "color": "#6366f1", "video_count": 0}` with HTTP 201.

Try creating it again (duplicate):
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/tags \
  -H "Content-Type: application/json" \
  -d '{"name":"test-freeform"}'
```
Expected: `409`

Clean up the test tag (find its id from the first response):
```bash
curl -s -X DELETE http://localhost:8000/api/tags/<id>
```

---

## Chunk 2: Web client tag creation input

### Task 2: Add inline tag creation to TagPicker.jsx

**Files:**
- Modify: `frontend/src/components/TagPicker.jsx` (full rewrite — file is only 31 lines)

**Context:**
`TagPicker` currently imports only `useQuery` from React Query and renders a flat grid of tag toggle buttons. We need to add:
- `useState` from React (not currently imported)
- `useMutation` + `useQueryClient` from `@tanstack/react-query` (only `useQuery` is imported)
- `createTag` from `../api.js` (only `fetchTags` is imported)

The `createTag` helper in `api.js` calls `req()`, which throws `new Error(err.detail)` on non-ok responses. The 409 detail text is `"Tag name already exists"`, so we check `e.message` in `onError` to distinguish duplicate from other failures.

React Query v5 syntax is required throughout (object form: `useMutation({ mutationFn: fn })`).

- [ ] **Step 1: Replace `TagPicker.jsx` with the full updated component:**

```jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTags, createTag } from '../api.js'
import TagBadge from './TagBadge.jsx'

export default function TagPicker({ selectedIds = [], onChange }) {
  const qc = useQueryClient()
  const { data: tags = [] } = useQuery({ queryKey: ['tags'], queryFn: fetchTags })
  const [newTagName, setNewTagName] = useState('')
  const [tagError, setTagError] = useState('')

  const createMutation = useMutation({
    mutationFn: (name) => createTag({ name }),
    onSuccess: (newTag) => {
      qc.invalidateQueries({ queryKey: ['tags'] })
      onChange([...selectedIds, newTag.id])
      setNewTagName('')
      setTagError('')
    },
    onError: (e) => {
      const isDuplicate = e.message.toLowerCase().includes('already')
      setTagError(isDuplicate ? 'already exists' : 'error saving')
      setTimeout(() => setTagError(''), 2000)
    },
  })

  function toggle(tag) {
    if (selectedIds.includes(tag.id)) {
      onChange(selectedIds.filter(id => id !== tag.id))
    } else {
      onChange([...selectedIds, tag.id])
    }
  }

  function handleKeyDown(e) {
    if (e.key !== 'Enter') return
    const trimmed = newTagName.trim()
    if (!trimmed) return
    createMutation.mutate(trimmed)
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map(tag => (
        <button
          key={tag.id}
          onClick={() => toggle(tag)}
          className={`transition-all duration-150 cursor-pointer rounded-md
            ${selectedIds.includes(tag.id) ? 'ring-2 ring-offset-1' : 'opacity-50 hover:opacity-80'}`}
          style={selectedIds.includes(tag.id) ? { outlineColor: tag.color } : {}}
        >
          <TagBadge tag={tag} />
        </button>
      ))}
      <div className="relative">
        <input
          type="text"
          value={newTagName}
          onChange={e => setNewTagName(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="New tag…"
          className="text-xs px-2 py-1 rounded-md bg-surface-2 border border-border-dim
            text-text-secondary placeholder:text-text-muted focus:outline-none
            focus:border-border-default w-24"
          disabled={createMutation.isPending}
        />
        {tagError && (
          <span className="absolute left-0 -bottom-5 text-[10px] text-accent-rose whitespace-nowrap">
            {tagError}
          </span>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser**

- Open `http://localhost:5173` (run `npm run dev` in `frontend/` if not running)
- Open any video's detail panel
- In the Tags section, type a new tag name in the input and press Enter
- Confirm the tag appears immediately as a selected badge in the picker
- Confirm the `['tags']` cache refreshes (the new tag appears in the full list)
- Type the same name again and press Enter — confirm `"already exists"` message appears for ~2s
- Type in an empty input and press Enter — confirm nothing happens

---

## Chunk 3: Safari extension tag creation input

### Task 3: Add inline tag creation to the Safari popup

**Files:**
- Modify: `safari-extension/popup/popup.js` (two locations: `buildVideoUI` tag section + `attachListeners`)
- Modify: `safari-extension/popup/popup.css` (add `.new-tag-input` style)

**Context:**
The popup's `buildVideoUI` function builds the tag section around lines 326–358. After the `if (availableTags.length > 0)` block (line 344–349) and before the `tagsError` check (line 351), we append a text input unconditionally to `tagPillsContainer`. This ensures the input is always reachable even when all existing tags are selected.

In `attachListeners` (lines 424–486), we wire the input after the existing tag-selection listeners.

The `apiFetch` helper (unlike the web client's `req()`) returns a raw `Response` object — check `res.ok` to detect errors.

**Important:** After `render()` is called on success, the DOM is fully rebuilt and the input element is recreated blank. The `setTimeout` error-reset callback uses `document.getElementById('new-tag-input')` (not a captured reference) because the reference may be stale after a re-render.

### Step-by-step

- [ ] **Step 1: Add `.new-tag-input` CSS** to `safari-extension/popup/popup.css` (append at end of file):

```css
.new-tag-input {
  padding: 3px 8px;
  border-radius: 99px;
  font-size: 11px;
  font-family: var(--font);
  border: 1px dashed var(--border);
  background: transparent;
  color: var(--text-muted);
  outline: none;
  width: 80px;
  transition: border-color 0.1s, color 0.1s;
}

.new-tag-input::placeholder { color: var(--text-muted); }
.new-tag-input:focus { border-color: var(--sky); color: var(--text); }
```

- [ ] **Step 2: Add the input element in `buildVideoUI`**

In `popup.js`, locate this block (around lines 344–354):

```js
  if (availableTags.length > 0) {
    const dropdownMenu = el('div', { class: 'tag-dropdown-menu', id: 'tag-dropdown', style: 'display:none' }, dropdownItems);
    const addBtn = el('button', { class: 'pill add-tag', id: 'add-tag-btn' }, '+ add \u25BE');
    const wrapper = el('div', { class: 'tag-dropdown' }, [addBtn, dropdownMenu]);
    tagPillsContainer.appendChild(wrapper);
  }

  if (tagsError && allTags.length === 0) {
```

Insert the new-tag-input **between** those two blocks:

```js
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
```

- [ ] **Step 3: Wire the input in `attachListeners`**

In `attachListeners`, locate the end of the tag-selection block (around lines 465–474):

```js
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
```

Add the new-tag-input handler **immediately after** that block, before the dropdown-close listener:

```js
  // New tag creation
  const newTagInputEl = document.getElementById('new-tag-input');
  if (newTagInputEl) {
    // Prevent outside-click handler from closing the dropdown when user clicks the input
    newTagInputEl.addEventListener('click', function(e) { e.stopPropagation(); });

    newTagInputEl.addEventListener('keydown', function(e) {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      e.stopPropagation();
      const name = newTagInputEl.value.trim();
      if (!name) return;
      (async function() {
        try {
          const res = await apiFetch('/api/tags', {
            method: 'POST',
            body: JSON.stringify({ name: name }),
          });
          if (res.ok) {
            const tag = await res.json();
            state.allTags.push(tag);
            state.selectedTags = state.selectedTags.concat([tag.name]);
            render();
          } else {
            newTagInputEl.placeholder = 'Error \u2014 try again';
            setTimeout(function() {
              const el = document.getElementById('new-tag-input');
              if (el) el.placeholder = 'New tag\u2026';
            }, 2000);
          }
        } catch (_err) {
          newTagInputEl.placeholder = 'Error \u2014 try again';
          setTimeout(function() {
            const el = document.getElementById('new-tag-input');
            if (el) el.placeholder = 'New tag\u2026';
          }, 2000);
        }
      })();
    });
  }
```

- [ ] **Step 4: Verify in browser (before Xcode rebuild)**

Open `safari-extension/popup/popup.html` directly in any browser (Chrome/Firefox) for a quick syntax check — the extension APIs won't work but you can confirm no JS errors in DevTools.

- [ ] **Step 5: Rebuild in Xcode and test in Safari**

- Open the Xcode project generated by `xcrun safari-web-extension-converter`
- Build and run (Cmd+R)
- Enable the extension in Safari → Preferences → Extensions
- Navigate to a YouTube video and open the popup
- Type a new tag name in the `New tag…` input and press Enter
- Confirm the new tag appears as a selected pill and the input clears
- Confirm the new tag also appears in the web client's tag list (shared backend)
- Test with all existing tags selected — confirm the input is still visible
