# Reed — Design System

Reed is an agentic RAG frontend. Its design language is **dark-first, minimal, and performance-focused**. Every decision prioritises information density and clarity over decoration.

---

## Brand Identity

- **Name:** Reed (evokes reading, reed as a writing instrument, clarity of thought)
- **Personality:** Developer-grade precision with consumer-level polish. Intelligent, calm, fast.
- **Tone:** Quiet confidence. No gratuitous animations, no distracting chrome.

---

## Color Palette

Reed uses exactly **4 semantic roles**. Never introduce raw color values — always go through CSS custom properties.

| Role | Token | OKLCH value | Usage |
|---|---|---|---|
| Brand / Primary | `--primary` | `oklch(0.7 0.15 200)` | Teal. Buttons, active states, icons, focus rings, badges |
| Background | `--background` | `oklch(0.09 0 0)` | Near-black. Root page background |
| Surface | `--card` | `oklch(0.12 0 0)` | Slightly lifted surface for cards and message bubbles |
| Sidebar | `--sidebar` | `oklch(0.11 0 0)` | Navigation rail background |

Supporting neutrals are derived automatically from `--muted`, `--border`, `--input`, etc. Never add a fifth brand color without strong justification.

### Color Rules

- The design is **dark-only**. Do not add a light mode unless explicitly requested. Both `:root` and `.dark` blocks in `globals.css` carry identical values so accidental light-mode leakage is impossible.
- Use `oklch()` for all color definitions. This gives perceptually uniform brightness steps and avoids muddy intermediates.
- **Never use** `bg-white`, `text-black`, `bg-gray-*`, or any raw Tailwind palette class for semantic surfaces. Always use tokens (`bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, etc.).
- The accent color for hover states is `--accent` (`oklch(0.18 0.02 200)`), a very subtle teal-tinted dark surface.
- Status colors:
  - Success: `text-emerald-500` / `bg-emerald-500/5` / `border-emerald-500/20`
  - Error: `text-destructive` / `bg-destructive/5` / `border-destructive/20`
  - Primary tint: `bg-primary/10`, `bg-primary/15`, `bg-primary/20` for non-interactive decorative surfaces

---

## Typography

Two font families, no more.

| Role | Family | Tailwind class |
|---|---|---|
| Body & headings | Geist Sans | `font-sans` |
| Code / monospace | Geist Mono | `font-mono` |

### Typography Rules

- Body text: `text-sm` (14px) with `leading-relaxed` (line-height ~1.625).
- Labels, captions, metadata: `text-xs` (12px).
- Micro-labels (badges, timestamps, uppercase section titles): `text-[10px]` or `text-[11px]`.
- View headings inside panels: `text-sm font-semibold`.
- Page-level empty state headlines: `text-lg font-semibold`.
- Use `text-balance` on multi-line headings and `text-pretty` on body paragraphs to prevent orphaned words.
- **Never** use `font-serif` or any decorative typeface.
- The `R` logomark in the sidebar uses `font-mono font-bold` for a terminal-command feel.

---

## Spacing & Layout

### Page Shell

The app uses a **fixed sidebar + scrollable main content** shell:

```
<html bg-background>
  <body flex flex-row h-screen overflow-hidden>
    <aside w-14 lg:w-56 h-screen sticky top-0>   ← AppSidebar
    <main flex-1 overflow-hidden>                  ← active view
```

The sidebar collapses to icon-only (`w-14`) below `lg` and expands to a full label rail (`w-56`) at `lg+`.

### Spacing Scale

Always use Tailwind's default spacing scale. No arbitrary values (`p-[16px]`, etc.) unless unavoidable.

| Context | Value |
|---|---|
| View header height | `h-14` |
| View header horizontal padding | `px-4 lg:px-6` |
| Content area padding | `p-4 lg:p-6` |
| Card / section padding | `p-3` or `p-4` |
| Inline gap between icon + label | `gap-2` or `gap-2.5` |
| Between stacked items in a list | `gap-2` |
| Between major sections | `gap-5` or `gap-6` |

### Max Width

Readable content (chat messages, upload zone, forms) is constrained to `max-w-2xl mx-auto`. Never let prose span the full viewport.

---

## Border Radius

| Token | Value | Typical usage |
|---|---|---|
| `rounded-md` | `calc(radius * 0.8)` | Nav items, small interactive elements |
| `rounded-lg` | `var(--radius)` = `0.5rem` | Inputs, cards, buttons |
| `rounded-xl` | `calc(radius * 1.4)` | File cards, info blocks |
| `rounded-2xl` | `calc(radius * 1.8)` | Chat bubbles, drop zones, icon containers |
| `rounded-full` | — | Avatar circles only |

Message bubbles use asymmetric rounding: `rounded-2xl rounded-tr-sm` for user messages and `rounded-2xl rounded-tl-sm` for assistant messages to indicate directionality.

---

## Component Patterns

### View Structure

Every view follows the same three-region pattern:

```tsx
<div className="flex flex-col h-full min-h-0">
  {/* 1. Header bar — h-14, border-b, sticky */}
  <div className="flex items-center gap-2 px-4 lg:px-6 h-14 border-b border-border shrink-0">
    <Icon className="size-4 text-primary" />
    <h1 className="text-sm font-semibold text-foreground">View Title</h1>
  </div>

  {/* 2. Scrollable body */}
  <ScrollArea className="flex-1 min-h-0"> ... </ScrollArea>
  {/* — or — */}
  <div className="flex-1 overflow-auto p-4 lg:p-6"> ... </div>

  {/* 3. Footer action bar — optional, border-t */}
  <div className="shrink-0 border-t border-border p-4 lg:px-6"> ... </div>
</div>
```

### Empty States

Empty states are centered vertically in the scroll area with a branded icon container:

```tsx
<div className="flex flex-col items-center justify-center py-20 gap-6">
  <div className="size-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
    <Icon className="size-7 text-primary" />
  </div>
  <div className="text-center">
    <h2 className="text-lg font-semibold text-foreground mb-1">Headline</h2>
    <p className="text-sm text-muted-foreground max-w-xs text-balance">Supporting copy.</p>
  </div>
</div>
```

### Sidebar Navigation Items

Active item: `bg-accent text-accent-foreground font-medium`
Inactive item: `text-muted-foreground hover:text-foreground hover:bg-muted`
All items: `h-9 rounded-md px-2 lg:px-3 text-sm transition-colors`

### Cards / Info Blocks

```tsx
<div className="rounded-xl bg-muted/50 border border-border p-4">
```

For status-tinted cards (success / error):
```tsx
// success
"border-emerald-500/20 bg-emerald-500/5"
// error
"border-destructive/20 bg-destructive/5"
```

### Badges

- Brand accent: `bg-primary/10 text-primary border-0 text-[10px] px-1.5 py-0 h-4`
- Standard: use `variant="secondary"`
- Never use `variant="default"` (uses `--primary` as background — too heavy for inline use)

### Buttons

- Primary action: `<Button size="sm">` — uses `bg-primary text-primary-foreground`
- Secondary / outlined: `<Button size="sm" variant="outline">`
- Icon-only square: `size-8 p-0 rounded-lg`
- Never add a loading spinner prop — compose `<Loader2 className="size-3.5 animate-spin" />` inside the button manually

---

## Icons

Library: **lucide-react** exclusively.

| Size | Usage |
|---|---|
| `size-3` | Inline micro-icons (remove button `X`) |
| `size-3.5` | Button icons, small inline contexts |
| `size-4` | View header icons, nav icons |
| `size-7` | Empty state illustration icons |

Rules:
- Icons inside buttons use Tailwind `size-*` directly (no `data-icon` wrapper needed for custom icon buttons, only for shadcn `Button` with label text).
- Never use emojis as icons.
- Icon color should always reference a semantic token (`text-primary`, `text-muted-foreground`, `text-destructive`, etc.).

---

## Interactions & Animation

Reed is deliberately **low-animation**. Only two motion patterns exist:

1. **Thinking indicator** — three `animate-bounce` dots with staggered `animation-delay` (0ms, 150ms, 300ms). Used only in the assistant "typing" state.
2. **Transitions** — `transition-colors` on interactive elements (hover color changes). Duration uses Tailwind's default (150ms). No `transition-all` except on the upload drop zone where subtle scale (`scale-[1.01]`) also applies.

No entrance animations, no skeleton-to-content fades, no page transitions. Performance over flourish.

---

## Scrollbar

Custom scrollbar via `::-webkit-scrollbar` in `globals.css`:
- Width: `4px`
- Thumb: `oklch(0.25 0 0)` → hover `oklch(0.35 0 0)`
- Track: `transparent`

This applies globally. Do not override per-component.

---

## API Integration Pattern

All backend calls live in `lib/api.ts`. Components never call `fetch` directly.

```
NEXT_PUBLIC_API_URL   (default: http://localhost:8000)
```

Pattern for each endpoint:
1. Export a typed request/response interface alongside the function.
2. Throw a descriptive `Error` on non-2xx responses using the JSON body's `detail` field when available.
3. Components catch the error and surface it inline — never via `alert()` or `console.error` alone.

---

## File & Folder Conventions

```
app/
  globals.css         ← design tokens, fonts, scrollbar, keyframes
  layout.tsx          ← fonts loaded here, metadata, TooltipProvider wrapper
  page.tsx            ← shell: sidebar + view router, health + provider fetches

components/
  app-sidebar.tsx     ← navigation rail, API status indicator
  chat-view.tsx       ← chat interface + MessageBubble + ThinkingBubble
  upload-view.tsx     ← drag-drop upload + FileCard history
  library-view.tsx    ← session document list
  settings-view.tsx   ← health check, provider grid, endpoint reference

lib/
  api.ts              ← all backend calls, typed, no fetch in components
  utils.ts            ← cn() helper

docs/
  design-system.md    ← this file
  api-reference.md    ← backend endpoint documentation
  component-guide.md  ← component patterns and composition rules
```

Sub-components (e.g. `MessageBubble`, `ThinkingBubble`, `FileCard`) are co-located in the same file as their parent view. Extract to a separate file only when the component is used by more than one view.
