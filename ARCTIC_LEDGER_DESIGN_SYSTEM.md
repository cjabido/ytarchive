# Arctic Ledger — Design System Reference

> A cool-toned, data-dense UI theme built for financial applications.
> Light-mode only. Designed for both desktop and mobile (iOS Safari safe).

---

## 1. Theme Identity

| Property | Value |
|----------|-------|
| **Name** | Arctic Ledger |
| **Mood** | Clean, professional, financially trustworthy |
| **Mode** | Light only (no dark mode) |
| **Base** | Cool gray surfaces with navy text |
| **Accent philosophy** | Semantic color assignments — green = positive, rose = negative, amber = warning, sky = primary action, violet = investment/premium |

---

## 2. Color Palette

### 2.1 Surfaces (backgrounds)

| Token | Hex | Usage |
|-------|-----|-------|
| `surface-0` | `#f4f4f7` | Page background, app shell |
| `surface-1` | `#ffffff` | Cards, modals, sidebar, inputs (elevated) |
| `surface-2` | `#eeeef2` | Hover states, input backgrounds, subtle fills |
| `surface-3` | `#e4e4ea` | Active filter pills, secondary buttons, badges |
| `surface-4` | `#d8d8e0` | Scrollbar thumb, timeline dots (inactive) |

### 2.2 Borders

| Token | Hex | Usage |
|-------|-----|-------|
| `border-dim` | `#e2e2ea` | Card borders, dividers, input borders (resting) |
| `border-default` | `#d0d0da` | Modal borders, hover-state borders |
| `border-bright` | `#b8b8c8` | Scrollbar thumb hover |

### 2.3 Text

| Token | Hex | Usage |
|-------|-----|-------|
| `text-primary` | `#1a1a2e` | Headings, names, primary amounts, body text |
| `text-secondary` | `#5a5a72` | Descriptions, secondary info, sub-labels |
| `text-muted` | `#8a8aa0` | Labels, timestamps, metadata, uppercase section headers |

### 2.4 Accent Colors

Each accent has a solid variant and a `-dim` variant (8–10% opacity) for icon backgrounds and subtle fills.

| Token | Hex | Dim opacity | Semantic meaning |
|-------|-----|-------------|------------------|
| `accent-mint` | `#10b981` | 10% | Income, positive values, success, growth, confirmation |
| `accent-rose` | `#e84393` | 10% | Expenses, negative values, overdue, error, liabilities |
| `accent-amber` | `#f59e0b` | 10% | Warnings, due-soon, autopay indicator |
| `accent-sky` | `#0284c7` | 8% | Primary action, navigation active, links, transfers |
| `accent-violet` | `#7c3aed` | 8% | Investments, premium features, contributions |

### 2.5 Dim Variant Formula

```css
/* Solid → Dim pattern */
--color-accent-mint-dim: rgba(16, 185, 129, 0.10);   /* 10% */
--color-accent-rose-dim: rgba(232, 67, 147, 0.10);   /* 10% */
--color-accent-amber-dim: rgba(245, 158, 11, 0.10);  /* 10% */
--color-accent-sky-dim: rgba(2, 132, 199, 0.08);     /* 8% */
--color-accent-violet-dim: rgba(124, 58, 237, 0.08); /* 8% */
```

### 2.6 Semantic Color Assignments

| Concept | Color | Example |
|---------|-------|---------|
| Positive money (income, gains) | `accent-mint` | `+$3,250.00` in green |
| Negative money (expenses, losses) | `accent-rose` | `-$87.32` in rose |
| Neutral money (balances, cost basis) | `text-primary` | `$4,832.41` in dark navy |
| Liabilities (credit cards, loans) | `accent-rose` | Negative prefix with rose |
| Warning/due-soon | `accent-amber` | "Due in 2 days" badge |
| Primary action / active nav | `accent-sky` | Add buttons, active sidebar icons |
| Investment / contribution | `accent-violet` | Portfolio, recurring contributions |

---

## 3. Typography

### 3.1 Font Families

| Token | Stack | Usage |
|-------|-------|-------|
| `--font-sans` | `'DM Sans', system-ui, sans-serif` | All UI text — headings, labels, descriptions |
| `--font-mono` | `'JetBrains Mono', monospace` | Financial amounts, dates, codes, period labels (1H/2H) |

Load from Google Fonts:
```html
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
```

### 3.2 Text Rendering

```css
body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

### 3.3 Type Scale (used in practice)

| Class | Size | Usage |
|-------|------|-------|
| `text-[10px]` | 10px | Micro-labels, variance labels, period tags |
| `text-[11px]` | 11px | Category pills in detail panel, table headers |
| `text-xs` | 12px | Section headers, metadata, filter pills, badges, secondary amounts |
| `text-sm` | 14px | List item text, form inputs, button labels, amounts |
| `text-base` | 16px | Page title (in header), modal titles |
| `text-lg` | 18px | Metric card values (mobile), hero sub-values |
| `text-xl` | 20px | Greeting heading, auth page titles |
| `text-2xl` | 24px | Metric card values (desktop) — used with `sm:text-2xl` |
| `text-3xl` | 30px | Transaction detail amount, net worth hero |
| `text-4xl` | 36px | Net worth hero (desktop) — used with `sm:text-4xl` |

### 3.4 Financial Amount Formatting

All monetary values use this pattern:

```
font-mono font-semibold tabular-nums
```

- `font-mono` — JetBrains Mono for digit alignment
- `font-semibold` — weight 600 for visual prominence
- `tabular-nums` — fixed-width digits so columns align (via `font-variant-numeric: tabular-nums`)
- Amounts always include 2 decimal places: `$1,234.56`
- Positive prefix: `+$` with `text-accent-mint`
- Negative prefix: `-$` with `text-accent-rose` or `text-text-primary`
- Currency symbol `$` is never separated from the number

---

## 4. Layout System

### 4.1 App Shell

```
┌──────────────────────────────────────────┐
│ [Sidebar w-14] │ [Main Content flex-1]   │
│ fixed left     │ ml-14                   │
│ bg-surface-1   │ bg-surface-0            │
│ border-r       │                         │
│ z-40           │                         │
└──────────────────────────────────────────┘
```

- **Sidebar:** Fixed left, `w-14` (56px), `bg-surface-1`, `border-r border-border-dim`, full height
- **Main content:** `flex-1 ml-14` to offset the sidebar
- **App container:** `flex min-h-screen bg-surface-0`

### 4.2 Content Width

```
max-w-7xl mx-auto px-4 sm:px-6 lg:px-8
```

- Maximum content width: `max-w-7xl` (80rem / 1280px)
- Responsive horizontal padding: `px-4` → `sm:px-6` → `lg:px-8`
- Main content area: `py-6 space-y-6` (vertical rhythm)

### 4.3 Grid Patterns

| Pattern | Classes | Usage |
|---------|---------|-------|
| 4-col metric cards | `grid grid-cols-2 lg:grid-cols-4 gap-3` | Dashboard metrics, bills summary, cash flow summary |
| 3-col summary | `grid grid-cols-1 sm:grid-cols-3 gap-3` | Accounts net worth, transaction summary |
| 2-col with sidebar | `grid grid-cols-1 lg:grid-cols-3 gap-4` | Dashboard (2+1) |
| Content + fixed sidebar | `grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6` | Bills page |
| Content + wider sidebar | `grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6` | Cash flow page |
| Equal halves | `grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-4` | Asset allocation + chart |
| Form 2-col | `grid grid-cols-2 gap-3` | Amount + Date, Institution + Last Four |
| Form 3-col | `grid grid-cols-3 gap-3` | Snapshot breakdown fields |

### 4.4 Spacing Convention

- `gap-3` (12px) between grid items
- `gap-4` (16px) for larger grid gaps and stacked sections
- `gap-6` (24px) for primary content/sidebar separation
- `space-y-6` for top-level section spacing
- `space-y-4` for inner sections
- `space-y-2` for list items within a section

---

## 5. Component Patterns

### 5.1 Sticky Header

Every page uses this header pattern:

```html
<header class="sticky top-0 z-30 bg-surface-0/80 backdrop-blur-xl border-b border-border-dim">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex items-center justify-between h-14">
      <!-- Left: icon + title -->
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-{accent}-dim flex items-center justify-center">
          <Icon class="w-4 h-4 text-{accent}" />
        </div>
        <h1 class="text-base font-semibold text-text-primary">Page Title</h1>
      </div>
      <!-- Right: actions -->
    </div>
  </div>
</header>
```

Key details:
- Height: `h-14` (56px)
- Background: `bg-surface-0/80` (80% opacity) with `backdrop-blur-xl`
- Z-index: `z-30`
- Each page has a unique accent color for its header icon

| Page | Header Accent |
|------|---------------|
| Dashboard | `accent-sky` |
| Cash Flow | `accent-sky` |
| Bills | `accent-sky` |
| Accounts | `accent-violet` |
| Transactions | `accent-amber` |
| Assets | `accent-mint` |

### 5.2 Cards

**Standard card:**
```html
<div class="bg-surface-1 border border-border-dim rounded-xl p-4">
```

**Card with header row:**
```html
<div class="bg-surface-1 border border-border-dim rounded-xl">
  <div class="flex items-center justify-between px-4 py-3 border-b border-border-dim">
    <!-- Section header + action link -->
  </div>
  <div class="divide-y divide-border-dim">
    <!-- List items -->
  </div>
</div>
```

### 5.3 Metric Cards

```html
<div class="bg-surface-1 border border-border-dim rounded-xl p-4 animate-fade-in-up"
     style="animation-delay: {n}ms">
  <div class="flex items-start justify-between mb-3">
    <span class="text-xs font-medium text-text-muted uppercase tracking-wider">Label</span>
    <div class="w-7 h-7 rounded-lg flex items-center justify-center bg-{accent}-dim">
      <Icon class="w-3.5 h-3.5 text-{accent}" />
    </div>
  </div>
  <div class="text-lg sm:text-2xl font-mono font-semibold tabular-nums text-{accent}">
    $1,234.56
  </div>
  <!-- Optional: change indicator or subtitle -->
</div>
```

- Icon container: `w-7 h-7 rounded-lg` with `-dim` background
- Value: responsive `text-lg sm:text-2xl`
- Label: `text-xs font-medium text-text-muted uppercase tracking-wider`
- Stagger animation with `animationDelay: {i * 60}ms`

### 5.4 Section Headers

```html
<div class="flex items-center gap-2 mb-2">
  <Icon class="w-3.5 h-3.5 text-text-muted" />
  <h2 class="text-xs font-medium text-text-muted uppercase tracking-wider">
    Section Title (count)
  </h2>
</div>
```

Always: `text-xs font-medium text-text-muted uppercase tracking-wider`

### 5.5 List Rows

**Standard row (account/transaction):**
```html
<div class="group/row flex items-center gap-4 px-4 py-3.5
  bg-surface-1 border border-border-dim rounded-lg
  hover:bg-surface-2/60 hover:border-border-default
  transition-all duration-200">

  <!-- Icon: w-9 h-9 rounded-lg -->
  <!-- Info: flex-1 min-w-0 with truncate -->
  <!-- Amount: shrink-0 font-mono -->
  <!-- Hover actions: opacity-0 group-hover/row:opacity-100 -->
</div>
```

- Row spacing: `space-y-2` between rows
- Icon size in rows: `w-9 h-9` with `w-4 h-4` icon inside
- Hover reveal for edit/action buttons: `opacity-0 group-hover/row:opacity-100`

**Divider row (inside a card):**
```html
<div class="flex items-center justify-between px-4 py-3 hover:bg-surface-2/50 transition-colors">
```

### 5.6 Filter Pills

```html
<div class="flex items-center gap-1 p-1 bg-surface-1 border border-border-dim rounded-lg">
  <button class="px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 cursor-pointer
    {active ? 'bg-surface-3 text-text-primary shadow-sm' : 'text-text-muted hover:text-text-secondary'}">
    Label
  </button>
</div>
```

- Container: `p-1 bg-surface-1 border border-border-dim rounded-lg`
- Active: `bg-surface-3 text-text-primary shadow-sm`
- Inactive: `text-text-muted hover:text-text-secondary`
- Pill: `px-3 py-1.5 rounded-md text-xs font-medium`

### 5.7 Primary Action Button

```html
<button class="flex items-center gap-1.5 px-3 py-2 rounded-lg
  bg-accent-sky/10 hover:bg-accent-sky/20
  text-accent-sky text-xs font-semibold
  border border-accent-sky/15 hover:border-accent-sky/25
  transition-all duration-150 cursor-pointer">
  <Plus class="w-3.5 h-3.5" />
  Add Item
</button>
```

This is a "ghost" button style — tinted background with matching text, no solid fill. Variations exist for different accents:
- Sky (default actions): `bg-accent-sky/10 text-accent-sky`
- Violet (contributions): `bg-accent-violet/10 text-accent-violet`
- Mint (confirm/pay): `bg-accent-mint/10 text-accent-mint`

### 5.8 Full-Width Submit Button (in modals/forms)

```html
<button class="w-full mt-2 py-2.5 rounded-lg
  bg-accent-sky/15 hover:bg-accent-sky/25
  text-accent-sky text-sm font-semibold
  border border-accent-sky/20 hover:border-accent-sky/30
  transition-all duration-150
  flex items-center justify-center gap-2 cursor-pointer">
  <Icon class="w-4 h-4" />
  Submit Label
</button>
```

### 5.9 Auth Buttons (solid fill exception)

The only solid-fill button in the system:
```html
<button class="w-full py-2 bg-accent-sky text-white text-sm font-semibold rounded-lg
  hover:bg-accent-sky/90 disabled:opacity-50">
```

### 5.10 Modals / Dialogs

```html
<div class="fixed inset-0 z-50 flex items-center justify-center">
  <!-- Backdrop -->
  <div class="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={onClose} />

  <!-- Panel -->
  <div class="relative z-10 w-full max-w-md mx-4
    bg-surface-1 border border-border-default rounded-2xl
    shadow-2xl shadow-black/10 animate-fade-in-up">

    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-border-dim">
      <h2 class="text-base font-semibold text-text-primary">Title</h2>
      <button class="w-8 h-8 rounded-lg flex items-center justify-center
        hover:bg-surface-3 text-text-muted hover:text-text-secondary
        transition-colors cursor-pointer">
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Body -->
    <form class="p-6 space-y-4">
      <!-- Fields -->
    </form>
  </div>
</div>
```

Key details:
- Backdrop: `bg-black/20 backdrop-blur-sm`
- Panel: `rounded-2xl` (larger radius than cards), `border-border-default` (stronger border)
- Max widths: `max-w-md` (standard), `max-w-sm` (compact — detail panels, confirm dialogs)
- Shadow: `shadow-2xl shadow-black/10`
- Z-index: `z-50`
- Close button: `w-8 h-8 rounded-lg`

### 5.11 Form Inputs

**Text input:**
```html
<input class="w-full px-3 py-2.5 rounded-lg
  bg-surface-2 border border-border-dim
  text-sm text-text-primary placeholder:text-text-muted
  focus:outline-none focus:border-accent-sky/50 focus:ring-1 focus:ring-accent-sky/20
  transition-colors" />
```

**Currency input:**
```html
<div class="relative">
  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-text-muted">$</span>
  <input class="w-full pl-7 pr-3 py-2.5 rounded-lg ... font-mono" />
</div>
```

**Select:**
```html
<select class="w-full px-3 py-2.5 rounded-lg appearance-none
  bg-surface-2 border border-border-dim
  text-sm text-text-primary
  focus:outline-none focus:border-accent-sky/50 focus:ring-1 focus:ring-accent-sky/20
  transition-colors cursor-pointer" />
```

**Search input:**
```html
<div class="relative animate-fade-in-up">
  <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
  <input class="w-48 pl-9 pr-3 py-2 rounded-lg
    bg-surface-1 border border-border-dim
    text-sm text-text-primary placeholder:text-text-muted
    focus:outline-none focus:border-accent-sky/40
    transition-colors" />
</div>
```

**Form label:**
```html
<label class="block text-xs font-medium text-text-muted uppercase tracking-wider mb-1.5">
```

**Checkbox:**
```html
<input type="checkbox" class="w-4 h-4 rounded border-border-default
  text-accent-sky focus:ring-accent-sky/30 cursor-pointer accent-accent-sky" />
```

### 5.12 Sidebar Navigation

```html
<nav class="fixed left-0 top-0 bottom-0 w-14 bg-surface-1 border-r border-border-dim
  flex flex-col items-center py-4 gap-2 z-40">

  <!-- Logo -->
  <div class="w-8 h-8 rounded-lg bg-accent-sky/15 flex items-center justify-center mb-4">
    <span class="text-sm font-bold text-accent-sky font-mono">F</span>
  </div>

  <!-- Nav button -->
  <button class="w-10 h-10 rounded-lg flex items-center justify-center
    transition-all duration-150 cursor-pointer
    {active ? 'bg-accent-sky-dim text-accent-sky' : 'text-text-muted hover:text-text-secondary hover:bg-surface-2'}">
    <Icon class="w-[18px] h-[18px]" />
  </button>

  <!-- Settings pushed to bottom -->
  <button class="mt-auto ...">
</nav>
```

- Icon size: `w-[18px] h-[18px]` (custom 18px)
- Button: `w-10 h-10 rounded-lg`
- Active: `bg-accent-sky-dim text-accent-sky`
- Settings uses `mt-auto` to push to bottom

### 5.13 Dropdowns

```html
<div class="absolute top-full left-0 mt-1 z-20 w-44
  bg-surface-1 border border-border-default rounded-lg
  shadow-lg shadow-black/10 py-1 animate-fade-in-up">
  <button class="w-full text-left px-3 py-2 text-xs cursor-pointer transition-colors
    {selected ? 'text-text-primary bg-surface-2 font-medium' : 'text-text-secondary hover:bg-surface-2'}">
```

### 5.14 Status Indicators

**Dot + label:**
```html
<div class="flex items-center gap-1.5">
  <div class="w-2 h-2 rounded-full bg-accent-mint" />
  <span class="text-xs text-accent-mint font-medium">Paid</span>
</div>
```

| Status | Dot Color | Text Color | Animation |
|--------|-----------|------------|-----------|
| Paid | `bg-accent-mint` | `text-accent-mint` | none |
| Overdue | `bg-accent-rose` | `text-accent-rose` | `animate-pulse-glow` |
| Due soon | `bg-accent-amber` | `text-accent-amber` | none |
| Upcoming | `bg-surface-4` | `text-text-muted` | none |

**Badge/tag:**
```html
<span class="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-text-muted font-medium">
  Inactive
</span>
```

### 5.15 Empty States

```html
<div class="py-16 text-center">
  <div class="w-12 h-12 rounded-xl bg-surface-2 flex items-center justify-center mx-auto mb-3">
    <Icon class="w-5 h-5 text-text-muted" />
  </div>
  <p class="text-sm text-text-muted">No items match your filter</p>
</div>
```

### 5.16 Progress Bars

```html
<div class="h-2 bg-surface-2 rounded-full overflow-hidden">
  <div class="h-full rounded-full transition-all duration-500 bg-accent-mint"
    style="width: 65%; opacity: 0.5" />
</div>
```

- Track: `h-2 bg-surface-2 rounded-full overflow-hidden`
- Fill: `rounded-full transition-all duration-500` with inline `width` and `opacity: 0.5–0.7`
- Thin variant: `h-1.5` (budget variance bars)
- Stacked bar (spending breakdown): `h-3 rounded-full flex` with multiple children

### 5.17 Collapsible Groups

```html
<button class="flex items-center justify-between w-full mb-2 group cursor-pointer">
  <div class="flex items-center gap-2">
    {collapsed ? <ChevronRight /> : <ChevronDown />}  <!-- w-3.5 h-3.5 text-text-muted -->
    <Icon class="w-3.5 h-3.5 text-{accent}" />
    <h2 class="text-xs font-medium text-text-muted uppercase tracking-wider">Group Name</h2>
    <span class="text-xs text-text-muted">(count)</span>
  </div>
  <span class="text-sm font-mono font-semibold tabular-nums text-{accent}">
    $subtotal
  </span>
</button>
```

### 5.18 Timeline

```html
<div class="flex items-center gap-3 py-2.5">
  <div class="flex flex-col items-center w-4 shrink-0">
    <div class="w-2.5 h-2.5 rounded-full border-2
      {overdue ? 'border-accent-rose bg-accent-rose/30' :
       dueSoon ? 'border-accent-amber bg-accent-amber/30' :
       'border-surface-4 bg-surface-3'}" />
    {notLast && <div class="w-px h-full min-h-[16px] bg-border-dim mt-1" />}
  </div>
  <!-- Content -->
</div>
```

---

## 6. Iconography

### 6.1 Icon Library

**lucide-react** — lightweight, consistent stroke icons.

### 6.2 Icon Sizes

| Context | Size | Class |
|---------|------|-------|
| Sidebar nav | 18px | `w-[18px] h-[18px]` |
| Card icon badge (large) | 16px | `w-4 h-4` |
| Card icon badge (small) | 14px | `w-3.5 h-3.5` |
| Section header | 14px | `w-3.5 h-3.5` |
| Inline (change arrow) | 12px | `w-3 h-3` |
| Empty state | 20px | `w-5 h-5` |

### 6.3 Icon Badge Containers

| Size | Padding class | Usage |
|------|---------------|-------|
| `w-7 h-7` | `rounded-lg bg-{accent}-dim` | Metric card icons |
| `w-8 h-8` | `rounded-lg bg-{accent}-dim` | Header icons, small list icons |
| `w-9 h-9` | `rounded-lg bg-{accent}-dim` | List row icons (accounts, transactions, assets) |
| `w-12 h-12` | `rounded-xl bg-surface-2` | Empty state icons |

---

## 7. Animations

### 7.1 Entrance Animation

```css
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
  animation: fade-in-up 0.4s ease-out both;
}
```

Used on: cards, list items, modals, search input reveal.
Staggered via `style={{ animationDelay: '{n}ms' }}` — typically 40–60ms per item.

### 7.2 Pulse Glow

```css
@keyframes pulse-glow {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.animate-pulse-glow {
  animation: pulse-glow 2s ease-in-out infinite;
}
```

Used on: overdue status dots only.

### 7.3 Transitions

Standard: `transition-all duration-150` (buttons, pills, hover states)
Relaxed: `transition-all duration-200` (list row hover)
Slow: `transition-all duration-500` (progress bar fills)

---

## 8. Charts & Data Visualization

### 8.1 SVG Line Charts (Sparklines & Growth)

- **Stroke:** `2–2.5px` with `strokeLinecap="round" strokeLinejoin="round"`
- **Area fill:** Linear gradient from `accent/12%` at top to `accent/0%` at bottom
- **End dot:** Solid circle `r=3–4` with optional halo `r=8 opacity=0.15`
- **Grid lines:** Dashed (`strokeDasharray="4 4"`), `border-dim` color
- **Axis labels:** `font-mono` for Y-axis values, `font-sans` for X-axis months
- **Colors:** Positive = `accent-mint`, Negative = `accent-rose`

### 8.2 Stacked Bar (Allocation)

```html
<div class="h-3 rounded-full bg-surface-2 overflow-hidden flex">
  {segments.map(seg =>
    <div class="h-full first:rounded-l-full last:rounded-r-full"
      style="width: {pct}%; backgroundColor: var(--color-{accent}); opacity: 0.65" />
  )}
</div>
```

### 8.3 Color Legend Pattern

```html
<div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
  <div class="flex items-center gap-2">
    <div class="w-2 h-2 rounded-full bg-{color}" style="opacity: 0.7" />
    <span class="text-xs text-text-secondary truncate">Category</span>
    <span class="text-xs font-mono text-text-muted tabular-nums">$amount</span>
  </div>
</div>
```

---

## 9. Custom Scrollbar

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--color-surface-4); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--color-border-bright); }
```

Thin (6px), subtle, matches surface palette. Only visible on WebKit browsers.

---

## 10. Mobile Considerations

### 10.1 Prevent Horizontal Scrolling

**Critical rule:** The app must never scroll horizontally. Apply to all pages:

```html
<div class="min-h-screen bg-surface-0 overflow-x-hidden">
```

This is applied on: AccountsPage, TransactionsPage, AssetTrackerPage, CashFlowPage. Any page with wide content (tables, multi-column layouts) MUST include `overflow-x-hidden` on the root page wrapper.

**Additional checks:**
- All text containers must use `min-w-0` and `truncate` to prevent text overflow
- Fixed-width elements (amounts, icons) must use `shrink-0`
- Tables with many columns should wrap in `overflow-x-auto` with a `min-w-[440px]` inner container
- Responsive padding: `px-4` on mobile, `sm:px-6`, `lg:px-8` on larger screens
- Test at 320px viewport width minimum

### 10.2 iOS Safe Area / Bottom Spacing

**Critical rule:** Content at the bottom of scrollable pages must not be blocked by or accidentally trigger iOS Safari's bottom navigation bar (home indicator area, address bar, back/forward buttons).

**Required patterns:**
- Every page's `<main>` element uses `py-6` which provides 24px bottom padding
- For pages with interactive elements near the bottom (buttons, form fields), add extra bottom padding:
  ```html
  <main class="... pb-20"> <!-- 80px safe zone on mobile -->
  ```
- Modals use `fixed inset-0` which inherently avoids the safe area issue
- The sidebar navigation uses `fixed left-0 top-0 bottom-0` — on mobile, consider whether a bottom tab bar replaces it

**iOS-specific CSS (add if needed):**
```css
@supports (padding-bottom: env(safe-area-inset-bottom)) {
  .safe-bottom {
    padding-bottom: calc(1.5rem + env(safe-area-inset-bottom));
  }
}
```

**Also add to the HTML viewport meta:**
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
```

### 10.3 Responsive Patterns Used

| Pattern | Mobile | Desktop |
|---------|--------|---------|
| Metric cards | `grid-cols-2` | `lg:grid-cols-4` |
| Summary cards | `grid-cols-1` | `sm:grid-cols-3` |
| Main + sidebar | Single column | `lg:grid-cols-3` or `lg:grid-cols-[1fr_300px]` |
| Amount text | `text-lg` | `sm:text-2xl` |
| Hero amount | `text-3xl` | `sm:text-4xl` |
| Export label | Hidden | `hidden sm:inline` |
| Table columns | Fewer cols | `hidden sm:flex` for optional columns |
| Row action buttons | Always visible OR touch targets | `hidden sm:flex` hover-reveal on desktop |
| Form grids | Stack to `grid-cols-1` | `grid-cols-2` or `grid-cols-3` |

### 10.4 Touch Target Sizes

All interactive elements meet the 44x44px minimum:
- Sidebar buttons: `w-10 h-10` (40px) with `gap-2` padding = sufficient
- Action buttons: `w-8 h-8` (32px) — consider increasing for mobile
- Filter pills: `px-3 py-1.5` — adequate touch target with internal padding
- List rows: `py-3` to `py-3.5` — sufficient vertical touch area

---

## 11. Tailwind CSS v4 Setup

This theme uses **Tailwind CSS v4** with the `@tailwindcss/vite` plugin. No `tailwind.config.js` — all tokens are defined via `@theme` in CSS.

### 11.1 Minimal CSS File

```css
@import "tailwindcss";

@theme {
  --color-surface-0: #f4f4f7;
  --color-surface-1: #ffffff;
  --color-surface-2: #eeeef2;
  --color-surface-3: #e4e4ea;
  --color-surface-4: #d8d8e0;

  --color-border-dim: #e2e2ea;
  --color-border-default: #d0d0da;
  --color-border-bright: #b8b8c8;

  --color-text-primary: #1a1a2e;
  --color-text-secondary: #5a5a72;
  --color-text-muted: #8a8aa0;

  --color-accent-mint: #10b981;
  --color-accent-mint-dim: rgba(16, 185, 129, 0.10);
  --color-accent-rose: #e84393;
  --color-accent-rose-dim: rgba(232, 67, 147, 0.10);
  --color-accent-amber: #f59e0b;
  --color-accent-amber-dim: rgba(245, 158, 11, 0.10);
  --color-accent-sky: #0284c7;
  --color-accent-sky-dim: rgba(2, 132, 199, 0.08);
  --color-accent-violet: #7c3aed;
  --color-accent-violet-dim: rgba(124, 58, 237, 0.08);

  --font-sans: 'DM Sans', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

### 11.2 Usage in Tailwind Classes

All tokens are usable as Tailwind utilities:
```html
<div class="bg-surface-1 text-text-primary border-border-dim">
<span class="text-accent-mint font-mono">
<div class="bg-accent-sky-dim">
```

---

## 12. Dependency Summary

| Dependency | Purpose |
|------------|---------|
| `tailwindcss` | Utility CSS framework (v4) |
| `@tailwindcss/vite` | Vite integration plugin |
| `lucide-react` | Icon library |
| `date-fns` | Date formatting (`format`, `differenceInDays`, etc.) |
| `DM Sans` (Google Fonts) | Primary UI typeface |
| `JetBrains Mono` (Google Fonts) | Monospace typeface for financial figures |

---

## 13. Design Checklist for New Pages

- [ ] Root wrapper: `<div class="min-h-screen bg-surface-0 overflow-x-hidden">`
- [ ] Sticky header with `bg-surface-0/80 backdrop-blur-xl border-b border-border-dim`
- [ ] Header icon uses a page-specific accent color
- [ ] Content wrapped in `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6`
- [ ] Cards use `bg-surface-1 border border-border-dim rounded-xl`
- [ ] Section headers use `text-xs font-medium text-text-muted uppercase tracking-wider`
- [ ] Amounts use `font-mono font-semibold tabular-nums` with semantic accent colors
- [ ] Text containers use `min-w-0` and `truncate` to prevent overflow
- [ ] Staggered `animate-fade-in-up` on visible content
- [ ] No horizontal scroll at 320px viewport width
- [ ] Sufficient bottom padding for iOS safe area (`py-6` minimum, `pb-20` if interactive elements at bottom)
- [ ] Filter pills / tabs use the standard pill container pattern
- [ ] Action buttons use ghost style (`bg-accent/10 text-accent border border-accent/15`)
- [ ] Modals use `z-50`, backdrop with `bg-black/20 backdrop-blur-sm`, `rounded-2xl`
- [ ] Form inputs use `bg-surface-2 border border-border-dim rounded-lg` with sky focus ring
- [ ] Responsive grid breakpoints tested: mobile → `sm` → `lg`
- [ ] Touch targets >= 44px on interactive elements
