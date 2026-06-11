# Reed — API Reference

All requests are made to the FastAPI backend. The base URL is controlled by the `NEXT_PUBLIC_API_URL` environment variable (default: `http://localhost:8000`).

All API logic is centralised in `lib/api.ts`. **Never call `fetch` directly from a component.**

---

## Environment

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

Set this in the Vercel project settings (Vars tab) or in a local `.env.local` file.

---

## Endpoints

### Health Check

```
GET /health
```

Returns the operational status of the backend.

**Response**
```json
{
  "status": "healthy",
  "message": "RAG system is operational"
}
```

Used by: `settings-view.tsx` (manual refresh button), `app/page.tsx` (initial load status indicator in sidebar).

---

### List Providers

```
GET /api/v1/providers
```

Returns all configured LLM provider names.

**Response**
```json
{
  "providers": ["openai", "anthropic", "ollama"]
}
```

Used by: `app/page.tsx` to populate the provider selector in the chat header.

---

### Upload Document

```
POST /api/v1/upload
Content-Type: multipart/form-data
```

**Request body**

| Field | Type | Description |
|---|---|---|
| `file` | `File` (PDF) | The PDF document to index |

**Response**
```json
{
  "filename": "report.pdf",
  "status": "Successfully processed 42 chunks"
}
```

The `status` string is parsed with `/(\d+)\s+chunk/` to extract the chunk count displayed in the upload card.

**Error** — non-2xx returns a JSON body with `detail` string. The frontend surfaces this inline on the file card.

Used by: `upload-view.tsx`.

---

### Chat / Query

```
POST /api/v1/chat
Content-Type: application/json
```

This is a **blocking** endpoint — the response arrives only after the full agentic RAG pipeline completes (retrieve → grade → generate → hallucination check → usefulness check). Do not add a timeout shorter than 60 seconds.

**Request body**
```json
{
  "question": "What are the main conclusions?",
  "provider": "openai"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | string | Yes | The user's question |
| `provider` | string | No | Override the LLM provider. Omit to use backend default. |

**Response**
```json
{
  "question": "What are the main conclusions?",
  "generation": "The document concludes that…",
  "provider_used": "openai"
}
```

The `generation` field is rendered as the assistant message. `provider_used` is shown as a teal badge beneath the bubble.

Used by: `chat-view.tsx`.

---

### List Documents *(planned)*

```
GET /api/v1/documents
```

Not yet implemented in the backend. The `library-view.tsx` shows a "coming soon" notice in its place. When this endpoint is implemented, it should return:

```json
{
  "documents": [
    { "filename": "report.pdf", "chunks": 42, "uploaded_at": "2025-06-11T10:00:00Z" }
  ]
}
```

---

## Error Handling Convention

All API functions in `lib/api.ts` follow this pattern:

```ts
const res = await fetch(...)
if (!res.ok) {
  const body = await res.json().catch(() => ({}))
  throw new Error(body.detail ?? `HTTP ${res.status}`)
}
return res.json()
```

Components catch the thrown `Error` and display `error.message` inline. No error is silently swallowed.
