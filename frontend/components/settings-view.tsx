'use client'

import { Settings, Activity, Zap, Server, CheckCircle2, XCircle, Loader2, RefreshCw, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

interface SettingsViewProps {
  isOnline: boolean | null
  providers: string[]
  onRefreshHealth: () => void
  isCheckingHealth: boolean
  baseUrl: string
}

const ENDPOINT_LIST = [
  { method: 'GET', path: '/health', status: 'live', desc: 'Liveness check' },
  { method: 'GET', path: '/api/v1/providers', status: 'live', desc: 'List LLM providers' },
  { method: 'POST', path: '/api/v1/chat', status: 'live', desc: 'Agentic RAG query' },
  { method: 'POST', path: '/api/v1/upload', status: 'live', desc: 'PDF ingestion pipeline' },
  { method: 'POST', path: '/api/v1/chat/stream', status: 'planned', desc: 'Streaming response (SSE)' },
  { method: 'GET', path: '/api/v1/documents', status: 'planned', desc: 'List indexed documents' },
  { method: 'DELETE', path: '/api/v1/documents/{id}', status: 'planned', desc: 'Remove document' },
]

export function SettingsView({ isOnline, providers, onRefreshHealth, isCheckingHealth, baseUrl }: SettingsViewProps) {
  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 lg:px-6 h-14 border-b border-border shrink-0">
        <Settings className="size-4 text-primary" />
        <h1 className="text-sm font-semibold text-foreground">Settings & Status</h1>
      </div>

      <div className="flex-1 overflow-auto p-4 lg:p-6">
        <div className="max-w-2xl mx-auto flex flex-col gap-5">
          {/* Health Card */}
          <section>
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mb-3">
              Backend connection
            </p>
            <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
              <div
                className={cn(
                  'size-10 rounded-xl flex items-center justify-center shrink-0',
                  isOnline === null
                    ? 'bg-muted'
                    : isOnline
                    ? 'bg-emerald-500/10'
                    : 'bg-destructive/10'
                )}
              >
                {isOnline === null ? (
                  <Activity className="size-5 text-muted-foreground" />
                ) : isOnline ? (
                  <CheckCircle2 className="size-5 text-emerald-500" />
                ) : (
                  <XCircle className="size-5 text-destructive" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <p className="text-sm font-medium text-foreground">API Status</p>
                  <Badge
                    variant="secondary"
                    className={cn(
                      'text-[10px] px-1.5 py-0 h-4 border-0',
                      isOnline === null
                        ? 'bg-muted text-muted-foreground'
                        : isOnline
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-destructive/10 text-destructive'
                    )}
                  >
                    {isOnline === null ? 'checking' : isOnline ? 'online' : 'offline'}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground font-mono truncate">{baseUrl}</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={onRefreshHealth}
                disabled={isCheckingHealth}
                className="shrink-0 h-7 text-xs gap-1.5"
              >
                {isCheckingHealth ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <RefreshCw className="size-3" />
                )}
                Refresh
              </Button>
            </div>
          </section>

          <Separator />

          {/* Providers */}
          <section>
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mb-3">
              LLM Providers
            </p>
            {providers.length === 0 ? (
              <div className="rounded-xl border border-border bg-card p-4 text-center">
                <p className="text-xs text-muted-foreground">
                  {isOnline === false
                    ? 'Cannot fetch providers — API is offline.'
                    : 'Loading providers…'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {providers.map((p) => (
                  <div
                    key={p}
                    className="flex items-center gap-2.5 rounded-xl border border-border bg-card px-3 py-2.5"
                  >
                    <Zap className="size-3.5 text-primary shrink-0" />
                    <span className="text-xs font-medium text-foreground capitalize">{p}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <Separator />

          {/* Endpoints */}
          <section>
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mb-3">
              API Endpoints
            </p>
            <div className="rounded-xl border border-border overflow-hidden">
              {ENDPOINT_LIST.map((ep, i) => (
                <div
                  key={ep.path}
                  className={cn(
                    'flex items-center gap-3 px-4 py-2.5',
                    i < ENDPOINT_LIST.length - 1 && 'border-b border-border'
                  )}
                >
                  <span
                    className={cn(
                      'text-[10px] font-mono font-bold px-1.5 py-0.5 rounded shrink-0',
                      ep.method === 'GET'
                        ? 'bg-sky-500/10 text-sky-400'
                        : ep.method === 'POST'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-red-500/10 text-red-400'
                    )}
                  >
                    {ep.method}
                  </span>
                  <span className="text-xs font-mono text-foreground flex-1 min-w-0 truncate">
                    {ep.path}
                  </span>
                  <span className="text-[11px] text-muted-foreground hidden sm:block truncate max-w-[140px]">
                    {ep.desc}
                  </span>
                  <Badge
                    variant="secondary"
                    className={cn(
                      'text-[10px] px-1.5 py-0 h-4 border-0 shrink-0',
                      ep.status === 'live'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-muted text-muted-foreground'
                    )}
                  >
                    {ep.status}
                  </Badge>
                </div>
              ))}
            </div>
          </section>

          <Separator />

          {/* About */}
          <section>
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mb-3">
              About Reed
            </p>
            <div className="rounded-xl border border-border bg-card p-4 grid grid-cols-2 gap-4">
              {[
                { label: 'Stack', value: 'LangGraph · ChromaDB · FastAPI' },
                { label: 'Version', value: '0.1.0 (alpha)' },
                { label: 'Base URL', value: baseUrl },
                { label: 'Auth', value: 'None (open dev)' },
              ].map(({ label, value }) => (
                <div key={label}>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">
                    {label}
                  </p>
                  <p className="text-xs text-foreground font-medium font-mono break-all">{value}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
