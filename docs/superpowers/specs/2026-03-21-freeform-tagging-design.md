# Free-Form Tagging Design Spec

## Overview

Add the ability to create new tags on the fly from both the web client and the Safari extension. New tags use the server-side default color (`#6366f1`). No color picker is included in this phase.

## Approach

A text input is added at the bottom of each client's existing tag dropdown/picker. The user types a name and presses Enter to create and immediately select the tag. No new UI surfaces — `POST /api/tags` already exists but needs a duplicate-name guard added.

---

## Backend (`backend/routers/tags.py`)

### What changes

The `create_tag` handler currently does a bare `INSERT INTO tags` with no duplicate handling. The `tags` table has a `UNIQUE` constraint on `name`, so a duplicate insert raises `aiosqlite.IntegrityError`, which FastAPI surfaces as a 500. The handler must catch this and return a proper 409.

### Change

Wrap the INSERT in a `try/except aiosqlite.IntegrityError` block:

```python
try:
    await db.execute("INSERT INTO tags (name, color) VALUES (?, ?)", [...])
    await db.commit()
except aiosqlite.IntegrityError:
    raise HTTPException(status_code=409, detail="Tag name already exists")
```

This allows both clients to distinguish a duplicate-name error (409) from a genuine server error (5xx).

---

## Web Client (`frontend/src/components/TagPicker.jsx`)

### What changes

A text input is appended below the existing tag toggle buttons inside `TagPicker`. It uses `useMutation` from `@tanstack/react-query` (v5 object syntax: `useMutation({ mutationFn: createTag })`). The import for `useMutation` must be added alongside the existing `useQuery` import.

### Behavior

- Placeholder: `New tag…`
- On Enter with a non-empty trimmed value:
  1. Call `createTag({ name: trimmedValue })` via the mutation (color omitted — server applies default `#6366f1`)
  2. On success:
     - Invalidate the `['tags']` React Query cache so the new tag appears globally
     - Call `onChange([...selectedIds, newTag.id])` to select it immediately
     - Clear the input
  3. On 409 response (duplicate name):
     - Show inline error text `"already exists"` adjacent to the input
     - Auto-clear after 2 seconds, keep focus on the input
  4. On other error (5xx / network): show `"Error saving"` for 2 seconds, same auto-clear

### Constraints

- Empty or whitespace-only input: no-op on Enter
- No color picker — color is omitted from the request body entirely
- The input is always visible at the bottom of the picker
- `createTag` is already exported from `frontend/src/api.js` — no changes needed there
- `useMutation` must be imported from `@tanstack/react-query` (add to existing import line)
- React Query v5 syntax: `useMutation({ mutationFn: fn })`, not positional `useMutation(fn)`

---

## Safari Extension (`safari-extension/popup/popup.js`)

### What changes

A text input (`id: new-tag-input`) is added to the tag section of `buildVideoUI`. It must be rendered **outside** and **after** the `availableTags.length > 0` guard block — so it remains accessible even when all existing tags are already selected. The input is wired up in `attachListeners()`.

### Placement in `buildVideoUI`

Current structure (simplified):
```
tagPillsContainer
  └── existing selected tag pills
  └── [if availableTags.length > 0]
        └── "+ add ▼" button + dropdown menu with available tags
```

New structure:
```
tagPillsContainer
  └── existing selected tag pills
  └── [if availableTags.length > 0]
        └── "+ add ▼" button + dropdown menu with available tags
  └── new-tag-input (always rendered, outside the guard)
```

The input is appended to `tagPillsContainer` unconditionally, after the existing `availableTags.length > 0` block.

### Behavior

- Placeholder: `New tag…`
- `id`: `new-tag-input`
- On Enter with a non-empty trimmed value:
  1. Call `apiFetch('/api/tags', { method: 'POST', body: JSON.stringify({ name: trimmedValue }) })`
  2. On `res.ok` (success):
     - Parse response JSON to get the new tag object `{ id, name, color }`
     - Push the new tag object into `state.allTags`
     - Append the tag name to `state.selectedTags`
     - Call `render()` — the new tag appears as a selected pill; because `state.selectedTags` now includes the new name, the `availableTags` filter (`!selectedTags.includes(t.name)`) excludes it from the dropdown on re-render. The input clears as part of re-render (new DOM).
  3. On any error (4xx, 5xx, or thrown network error):
     - Set the input's placeholder to `"Error — try again"` for 2 seconds, then restore `"New tag…"`
     - Keep the dropdown open

### Event handling

- `click` on the input: `e.stopPropagation()` — prevents the document-level outside-click handler from closing the dropdown
- `keydown` on the input when key is Enter: `e.preventDefault()` + `e.stopPropagation()` before processing — prevents bubbling to any document listener
- Both handlers wired in `attachListeners()` via `document.getElementById('new-tag-input')`

### Constraints

- No color picker — color is omitted from the request body
- Empty or whitespace-only input: no-op on Enter
- The input is always rendered regardless of how many tags are selected

---

## Error Cases Summary

| Scenario | Web client | Safari extension |
|---|---|---|
| Duplicate tag name (409) | Inline `"already exists"` for 2s | Placeholder `"Error — try again"` for 2s |
| Server / network error | Inline `"Error saving"` for 2s | Placeholder `"Error — try again"` for 2s |
| Empty/whitespace input | No-op | No-op |
| All tags already selected | Input still visible (always rendered) | Input still visible (always rendered) |

---

## Files Changed

| File | Change |
|---|---|
| `backend/routers/tags.py` | Wrap INSERT in `try/except IntegrityError` → 409 |
| `frontend/src/components/TagPicker.jsx` | Add `useMutation` import + text input + mutation handler |
| `safari-extension/popup/popup.js` | Add `new-tag-input` to tag section + wire in `attachListeners` |
