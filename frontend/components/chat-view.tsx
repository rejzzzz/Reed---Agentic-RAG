'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Bot, User, AlertCircle, Loader2, Sparkles, Plus, Trash2, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { sendChat, streamChat, fetchChats, fetchChatHistory, deleteChat, fetchDocuments, type ChatResponse, type ChatSession, type ChatMessage, type DocumentItem } from '@/lib/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  provider?: string
  isError?: boolean
  timestamp: Date
}

interface ChatViewProps {
  providers: string[]
  defaultProvider?: string
}

const SUGGESTED_QUESTIONS = [
  'Summarize the key points of the uploaded document',
  'What are the main conclusions in the document?',
  'Extract any dates or deadlines mentioned',
  'What action items are discussed?',
]

export function ChatView({ providers, defaultProvider }: ChatViewProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState(defaultProvider ?? providers[0] ?? '')
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [selectedDocument, setSelectedDocument] = useState<string | undefined>()
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const loadDocuments = useCallback(async () => {
    try {
      const res = await fetchDocuments()
      setDocuments(res.documents)
    } catch (err) {
      console.error('Failed to load documents', err)
    }
  }, [])

  const loadSessions = useCallback(async () => {
    try {
      const res = await fetchChats()
      setSessions(res.sessions)
    } catch (err) {
      console.error('Failed to load sessions', err)
    }
  }, [])

  useEffect(() => {
    loadSessions()
    loadDocuments()
  }, [loadSessions, loadDocuments])

  const loadHistory = useCallback(async (sessionId: string) => {
    setLoadingHistory(true)
    try {
      const res = await fetchChatHistory(sessionId)
      const formattedMessages: Message[] = res.history.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        provider: m.provider,
        timestamp: new Date(m.timestamp)
      }))
      setMessages(formattedMessages)
      setActiveSessionId(sessionId)
      setSelectedDocument(res.document ?? undefined)
    } catch (err) {
      console.error('Failed to load history', err)
    } finally {
      setLoadingHistory(false)
    }
  }, [])

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await deleteChat(sessionId)
      if (activeSessionId === sessionId) {
        setActiveSessionId(undefined)
        setMessages([])
      }
      loadSessions()
    } catch (err) {
      console.error('Failed to delete session', err)
    }
  }

  const handleNewChat = () => {
    setActiveSessionId(undefined)
    setMessages([])
    setSelectedDocument(undefined)
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const submit = useCallback(
    async (question: string) => {
      if (!question.trim() || loading) return
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: question.trim(),
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])
      setInput('')
      setLoading(true)
      try {
        const tempId = crypto.randomUUID()
        const assistantMsg: Message = {
          id: tempId,
          role: 'assistant',
          content: '',
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, assistantMsg])
        
        let finalSessionId = activeSessionId
        
        streamChat(
          {
            question: question.trim(),
            provider: selectedProvider || undefined,
            session_id: activeSessionId,
            document: selectedDocument
          },
          (token) => {
            setLoading(false) // Hide thinking bubble once tokens arrive
            setMessages((prev) =>
              prev.map((m) => (m.id === tempId ? { ...m, content: m.content + token } : m))
            )
          },
          (metadata) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === tempId ? { ...m, provider: metadata.provider_used } : m))
            )
            if (!activeSessionId && metadata.session_id) {
              finalSessionId = metadata.session_id
            }
          },
          (error) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempId
                  ? { ...m, content: m.content + `\n\nError: ${error}`, isError: true }
                  : m
              )
            )
            setLoading(false)
          },
          () => {
            setLoading(false)
            if (finalSessionId !== activeSessionId) {
              setActiveSessionId(finalSessionId)
              loadSessions()
            }
            setTimeout(() => {
              textareaRef.current?.focus()
            }, 10)
          }
        )
      } catch (err) {
        setLoading(false)
        const errorMsg: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: err instanceof Error ? err.message : 'An unexpected error occurred.',
          isError: true,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorMsg])
        setLoading(false)
      }
    },
    [loading, selectedProvider, activeSessionId, loadSessions]
  )

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit(input)
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex h-full min-h-0">
      {/* Sidebar for Sessions */}
      <div className="w-64 border-r border-border bg-muted/20 flex flex-col hidden md:flex shrink-0">
        <div className="p-4 border-b border-border">
          <Button onClick={handleNewChat} className="w-full justify-start gap-2" variant="outline">
            <Plus className="size-4" />
            New Chat
          </Button>
        </div>
        <ScrollArea className="flex-1 min-h-0">
          <div className="p-2 flex flex-col gap-1">
            {sessions.map(session => (
              <div
                key={session.id}
                onClick={() => loadHistory(session.id)}
                className={cn(
                  "group flex items-center justify-between px-3 py-2 text-sm rounded-md cursor-pointer transition-colors",
                  activeSessionId === session.id ? "bg-accent text-accent-foreground font-medium" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <div className="flex items-center gap-2 truncate pr-2">
                  <MessageSquare className="size-3.5 shrink-0" />
                  <span className="truncate">{session.title}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(session.id, e)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>

      <div className="flex flex-col flex-1 h-full min-h-0">
        {/* Header */}
        <div className="flex items-center justify-between px-4 lg:px-6 h-14 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            <h1 className="text-sm font-semibold text-foreground">Chat</h1>
          </div>
          <div className="flex items-center gap-2">
            {documents.length > 0 && (
              <Select value={selectedDocument || "all"} onValueChange={(value) => setSelectedDocument(value === "all" ? undefined : (value ?? undefined))} disabled={!!activeSessionId}>
                <SelectTrigger className="h-7 text-xs w-[160px] bg-muted border-border">
                  <SelectValue placeholder="All Documents" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all" className="text-xs">All Documents</SelectItem>
                  {documents.map((d) => (
                    <SelectItem key={d.filename} value={d.filename} className="text-xs">
                      {d.filename}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {providers.length > 0 && (
              <Select value={selectedProvider} onValueChange={(value) => setSelectedProvider(value || '')}>
                <SelectTrigger className="h-7 text-xs w-[120px] bg-muted border-border">
                  <SelectValue placeholder="Provider" />
                </SelectTrigger>
                <SelectContent>
                  {providers.map((p) => (
                    <SelectItem key={p} value={p} className="text-xs capitalize">
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <Button variant="ghost" size="icon" className="md:hidden" onClick={handleNewChat}>
              <Plus className="size-4" />
            </Button>
          </div>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="max-w-3xl mx-auto px-4 lg:px-6">
            {loadingHistory ? (
              <div className="flex justify-center items-center h-full py-20">
                <Loader2 className="size-6 animate-spin text-muted-foreground" />
              </div>
            ) : isEmpty ? (
              <div className="flex flex-col items-center justify-center py-20 gap-6">
                <div className="size-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <Bot className="size-7 text-primary" />
                </div>
                <div className="text-center">
                  <h2 className="text-lg font-semibold text-foreground mb-1">Ask Reed anything</h2>
                  <p className="text-sm text-muted-foreground max-w-xs text-balance">
                    Upload a PDF and ask questions. Reed will retrieve and reason over your documents.
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => submit(q)}
                      className="text-left text-xs text-muted-foreground border border-border rounded-lg px-3 py-2.5 hover:border-primary/50 hover:text-foreground hover:bg-accent transition-colors leading-relaxed"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="py-6 flex flex-col gap-5">
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                {loading && <ThinkingBubble />}
                <div ref={bottomRef} />
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="shrink-0 border-t border-border p-4 lg:px-6">
          <div className="max-w-3xl mx-auto">
            <div className="relative flex items-end gap-2 bg-muted rounded-xl border border-border focus-within:border-primary/50 transition-colors p-2">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your documents…"
                rows={1}
                className="flex-1 resize-none bg-transparent border-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 text-sm placeholder:text-muted-foreground min-h-[36px] max-h-32 py-2 px-1"
                style={{ fieldSizing: 'content' } as React.CSSProperties}
              />
              <Button
                size="sm"
                onClick={() => submit(input)}
                disabled={!input.trim() || loading}
                className="shrink-0 size-8 p-0 rounded-lg"
              >
                {loading ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Send className="size-3.5" />
                )}
              </Button>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1.5 text-center">
              Press Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      {/* Avatar */}
      <div
        className={cn(
          'size-7 rounded-full flex items-center justify-center shrink-0 mt-0.5',
          isUser ? 'bg-secondary' : 'bg-primary/15 border border-primary/25'
        )}
      >
        {isUser ? (
          <User className="size-3.5 text-muted-foreground" />
        ) : message.isError ? (
          <AlertCircle className="size-3.5 text-destructive" />
        ) : (
          <Bot className="size-3.5 text-primary" />
        )}
      </div>

      {/* Bubble */}
      <div className={cn('flex flex-col gap-1 max-w-[80%]', isUser && 'items-end')}>
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : message.isError
              ? 'bg-destructive/10 text-destructive border border-destructive/20 rounded-tl-sm'
              : 'bg-card border border-border rounded-tl-sm'
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="flex items-center gap-2 px-1">
          {!isUser && message.provider && !message.isError && (
            <Badge
              variant="secondary"
              className="text-[10px] px-1.5 py-0 h-4 bg-primary/10 text-primary border-0 capitalize"
            >
              {message.provider}
            </Badge>
          )}
          <span className="text-[10px] text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </div>
  )
}

function ThinkingBubble() {
  return (
    <div className="flex gap-3">
      <div className="size-7 rounded-full bg-primary/15 border border-primary/25 flex items-center justify-center shrink-0 mt-0.5">
        <Bot className="size-3.5 text-primary" />
      </div>
      <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
        <span className="size-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:0ms]" />
        <span className="size-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
        <span className="size-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  )
}
