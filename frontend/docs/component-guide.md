# Reed — Component Guide

This document describes every component in the project: its responsibility, props, and the patterns it establishes. Read this before creating or modifying any UI file.

---

## Component Library

Reed uses **shadcn/ui** (style: `nova`, base: `base`, Tailwind v4). Components are installed as source code under `components/ui/`.

Installed components: `button`, `badge`, `tooltip`, `separator`, `scroll-area`, `skeleton`, `textarea`, `select`.

Add new components via:
```bash
pnpm dlx shadcn@latest add <component-name> --overwrite -y
```

**Never write a custom component if a shadcn component exists for the use case.**

---

## Application Components

### `AppSidebar`

**File:** `components/app-sidebar.tsx`
**Responsibility:** Fixed navigation rail. Icon-only at `< lg`, icon + label at `lg+`.

**Props**
```ts
interface AppSidebarProps {
  activeView: 'chat' | 'upload' | 'library' | 'settings'
  onViewChange: (view: ActiveView) => void
  isOnline: boolean | null   // null = checking, true = healthy, false = offline
  uploadCount: number        // shown as badge on Library nav item
}
```

**Key patterns:**
- Nav items are generated from a `navItems` array — add new views here, not inline.
- Active item style: `bg-accent text-accent-foreground font-medium`
- Inactive item style: `text-muted-foreground hover:text-foreground hover:bg-muted`
- Tooltips (`TooltipContent side="right"`) replace the hidden labels on mobile.
- The status dot at the bottom is: grey (`isOnline === null`), `bg-emerald-500` (true), `bg-destructive` (false).
- The `R` logomark uses `font-mono font-bold` — keep this, it is intentional branding.

---

### `ChatView`

**File:** `components/chat-view.tsx`
**Responsibility:** Full chat interface including message history, input bar, and provider selector.

**Props**
```ts
interface ChatViewProps {
  providers: string[]
  defaultProvider?: string
}
```

**Sub-components (co-located):**
- `MessageBubble` — renders a single message. User bubbles align right with `flex-row-reverse`.
- `ThinkingBubble` — three bouncing dots shown while `loading === true`.

**Key patterns:**
- The `submit()` function is wrapped in `useCallback` — preserve this to avoid stale closure issues.
- `Enter` submits; `Shift+Enter` inserts a newline (`handleKeyDown` guard).
- Auto-scroll uses a `bottomRef` div at the end of the message list + `useEffect` on `[messages, loading]`.
- The input grows vertically via `style={{ fieldSizing: 'content' }}` — this is a CSS-native approach, no JS resize logic needed.
- Empty state shows 4 suggested questions as clickable buttons that call `submit()` directly.
- The provider badge beneath assistant messages uses `bg-primary/10 text-primary` — do not change this to a standard variant.
- Error messages use `bg-destructive/10 text-destructive border border-destructive/20`.

**Adding new suggested questions:** Edit the `SUGGESTED_QUESTIONS` constant at the top of the file.

---

### `UploadView`

**File:** `components/upload-view.tsx`
**Responsibility:** PDF drag-and-drop upload with per-file status cards.

**Props**
```ts
interface UploadViewProps {
  onUploadSuccess: (filename: string) => void  // increments uploadCount in parent
}
```

**Sub-components (co-located):**
- `FileCard` — shows uploading/success/error state for one file.

**Key patterns:**
- Only `.pdf` files are accepted. Non-PDF files receive an immediate client-side error card — no API call is made.
- The drop zone applies `scale-[1.01]` + `border-primary` + `bg-primary/5` on drag-over.
- `processFile` is wrapped in `useCallback` with `onUploadSuccess` as dependency.
- Chunk count is extracted from the `status` string via `/(\d+)\s+chunk/` regex — fragile if the backend changes its message format. Update both the regex and this note if the backend changes.
- The info grid below the drop zone (format / processing / storage) is purely decorative — update it if the backend changes its pipeline.

---

### `LibraryView`

**File:** `components/library-view.tsx`
**Responsibility:** Lists documents indexed in the current session. Placeholder for the planned `GET /api/v1/documents` endpoint.

**Props**
```ts
interface LibraryViewProps {
  uploadedFiles: string[]   // filenames accumulated from successful UploadView uploads
}
```

**Key patterns:**
- Session-only list: data lives in the parent (`page.tsx`) state and is passed down. It is not persisted.
- When the `GET /api/v1/documents` endpoint is implemented, replace the prop-driven list with an SWR fetch. The "In development" `Alert` should be removed at that point.
- Empty state follows the standard pattern (icon container + headline + supporting copy).

---

### `SettingsView`

**File:** `components/settings-view.tsx`
**Responsibility:** API health check, provider grid, endpoint reference table, and about section.

**Props**
```ts
interface SettingsViewProps {
  providers: string[]
}
```

**Key patterns:**
- Health check is triggered on mount and on manual "Refresh" button click. It calls `GET /health` directly (not through SWR) because it is an explicit user action, not a background poll.
- Provider grid is display-only — it shows whatever the backend returns with no edit capability.
- The endpoint reference table has a `Live` / `Planned` badge column. Update this table when new backend endpoints are shipped.
- The "About" section at the bottom describes the agentic pipeline steps — update if the backend pipeline changes.

---

## Page Shell

**File:** `app/page.tsx`
**Responsibility:** Top-level layout, view routing, initial data fetches.

**State managed here:**
- `activeView` — which view is shown
- `providers` — fetched once on mount from `GET /api/v1/providers`
- `isOnline` — fetched once on mount from `GET /health`, passed to `AppSidebar`
- `uploadedFiles` — accumulated list of successfully uploaded filenames, passed to `LibraryView`

**Rules:**
- All `fetch` calls at this level use `useEffect` with empty dependency array (mount-only). They are not wrapped in SWR because they are one-shot loads, not polling subscriptions.
- If data-fetching needs to become reactive (polling, revalidation), migrate to SWR with a key.
- Do not add new views without also adding them to `AppSidebar`'s `navItems` array and the `ActiveView` union type.

---

## Adding a New View

1. Create `components/my-view.tsx` following the three-region structure (header bar / scrollable body / optional footer).
2. Export a typed `props` interface.
3. Add the view ID to the `ActiveView` union type in `app-sidebar.tsx`.
4. Add a nav entry to the `navItems` array in `app-sidebar.tsx`.
5. Add a case to the view-router in `app/page.tsx`.
6. If the view needs backend data, add the fetch function to `lib/api.ts`.

---

## Do Not

- Do not use `localStorage` for any state. All state is in-memory React state or fetched from the backend.
- Do not import components from `components/ui/` that have not been installed via the shadcn CLI.
- Do not add a light mode.
- Do not add page-level route navigation (Next.js `Link`, `useRouter`). Reed is a single-page app using view state, not URL routing.
- Do not use `space-x-*` / `space-y-*` for spacing. Use `flex` + `gap-*`.
- Do not use raw color values. Use semantic tokens only.
