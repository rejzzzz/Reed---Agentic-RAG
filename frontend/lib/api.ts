const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface HealthResponse {
  status: string
  message: string
}

export interface ProvidersResponse {
  available_providers: string[]
}

export interface ChatRequest {
  question: string
  provider?: string
}

export interface ChatResponse {
  question: string
  generation: string
  provider_used: string
}

export interface UploadResponse {
  filename: string
  status: string
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/health`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Health check failed')
  return res.json()
}

export async function fetchProviders(): Promise<ProvidersResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/providers`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch providers')
  return res.json()
}

export async function sendChat(payload: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.detail ?? 'Chat request failed')
  }
  return res.json()
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/api/v1/upload`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.detail ?? 'Upload failed')
  }
  return res.json()
}
