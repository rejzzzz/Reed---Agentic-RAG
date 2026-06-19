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
  session_id?: string
  document?: string
}

export interface ChatResponse {
  question: string
  generation: string
  provider_used: string
  session_id: string
}

export interface UploadResponse {
  filename: string
  status: string
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  provider?: string
  timestamp: string
}

export interface DocumentItem {
  filename: string
  chunk_count: number
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

export async function fetchChats(): Promise<{ sessions: ChatSession[] }> {
  const res = await fetch(`${BASE_URL}/api/v1/chats`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch chats')
  return res.json()
}

export async function fetchChatHistory(sessionId: string): Promise<{ session_id: string, document: string | null, history: ChatMessage[] }> {
  const res = await fetch(`${BASE_URL}/api/v1/chats/${sessionId}`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch chat history')
  return res.json()
}

export async function deleteChat(sessionId: string): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/api/v1/chats/${sessionId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete chat')
  return res.json()
}

export async function fetchDocuments(): Promise<{ documents: DocumentItem[], total_chunks: number }> {
  const res = await fetch(`${BASE_URL}/api/v1/documents`, { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch documents')
  return res.json()
}

export async function deleteDocument(filename: string): Promise<{ filename: string, deleted_chunks: number }> {
  const res = await fetch(`${BASE_URL}/api/v1/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete document')
  return res.json()
}

export function streamChat(
  request: ChatRequest,
  onToken: (token: string) => void,
  onMetadata: (metadata: { session_id: string; provider_used: string }) => void,
  onError: (error: string) => void,
  onDone: () => void
): () => void {
  const abortController = new AbortController();
  
  fetch(`${BASE_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
    signal: abortController.signal,
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error('Stream request failed');
    }
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    if (!reader) return;

    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';
      for (const block of lines) {
        const lineParts = block.split('\n');
        let event = '';
        let data = '';
        for (const part of lineParts) {
          if (part.startsWith('event: ')) event = part.slice(7);
          else if (part.startsWith('data: ')) data = part.slice(6);
        }
        if (event === 'token') {
          try {
            const parsed = JSON.parse(data);
            onToken(parsed.text);
          } catch (e) {}
        } else if (event === 'metadata') {
          try {
            const parsed = JSON.parse(data);
            onMetadata(parsed);
          } catch (e) {}
        } else if (event === 'error') {
          try {
            const parsed = JSON.parse(data);
            onError(parsed.detail);
          } catch (e) {}
        } else if (event === 'done') {
          onDone();
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError(err.message);
    }
  });

  return () => abortController.abort();
}
