'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Bot, User, AlertCircle, Loader2, Sparkles, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { sendChat, type ChatResponse } from '@/lib/api'

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
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState(defaultProvider ?? providers[0] ?? '')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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
        const res: ChatResponse = await sendChat({
          question: question.trim(),
          provider: selectedProvider || undefined,
        })
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: res.generation,
          provider: res.provider_used,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, assistantMsg])
      } catch (err) {
        const errorMsg: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: err instanceof Error ? err.message : 'An unexpected error occurred.',
          isError: true,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorMsg])
      } finally {
        setLoading(false)
        textareaRef.current?.focus()
      }
    },
    [loading, selectedProvider]
  )

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit(input)
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="flex items-center justify-between px-4 lg:px-6 h-14 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-primary" />
          <h1 className="text-sm font-semibold text-foreground">Chat</h1>
        </div>
        <div className="flex items-center gap-2">
          {providers.length > 0 && (
            <Select value={selectedProvider} onValueChange={setSelectedProvider}>
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
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="max-w-2xl mx-auto px-4 lg:px-6">
          {isEmpty ? (
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
        <div className="max-w-2xl mx-auto">
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
