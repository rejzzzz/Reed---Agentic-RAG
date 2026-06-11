'use client'

import { useState, useRef, useCallback } from 'react'
import { Upload, FileText, CheckCircle2, XCircle, Loader2, X, CloudUpload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { uploadDocument } from '@/lib/api'

interface UploadedFile {
  id: string
  filename: string
  status: 'uploading' | 'success' | 'error'
  message?: string
  chunks?: number
  timestamp: Date
}

interface UploadViewProps {
  onUploadSuccess: (filename: string) => void
}

export function UploadView({ onUploadSuccess }: UploadViewProps) {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const processFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        const errFile: UploadedFile = {
          id: crypto.randomUUID(),
          filename: file.name,
          status: 'error',
          message: 'Only PDF files are supported.',
          timestamp: new Date(),
        }
        setFiles((prev) => [errFile, ...prev])
        return
      }

      const id = crypto.randomUUID()
      const uploadingFile: UploadedFile = {
        id,
        filename: file.name,
        status: 'uploading',
        timestamp: new Date(),
      }
      setFiles((prev) => [uploadingFile, ...prev])

      try {
        const res = await uploadDocument(file)
        const chunkMatch = res.status.match(/(\d+)\s+chunk/)
        const chunks = chunkMatch ? parseInt(chunkMatch[1]) : undefined
        setFiles((prev) =>
          prev.map((f) =>
            f.id === id ? { ...f, status: 'success', message: res.status, chunks } : f
          )
        )
        onUploadSuccess(file.name)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Upload failed'
        setFiles((prev) =>
          prev.map((f) => (f.id === id ? { ...f, status: 'error', message: msg } : f))
        )
      }
    },
    [onUploadSuccess]
  )

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return
    Array.from(fileList).forEach(processFile)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => setIsDragging(false)

  const removeFile = (id: string) => setFiles((prev) => prev.filter((f) => f.id !== id))

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 lg:px-6 h-14 border-b border-border shrink-0">
        <Upload className="size-4 text-primary" />
        <h1 className="text-sm font-semibold text-foreground">Upload Documents</h1>
      </div>

      <div className="flex-1 overflow-auto p-4 lg:p-6">
        <div className="max-w-2xl mx-auto flex flex-col gap-5">
          {/* Drop Zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => inputRef.current?.click()}
            className={cn(
              'relative flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-10 cursor-pointer transition-all',
              isDragging
                ? 'border-primary bg-primary/5 scale-[1.01]'
                : 'border-border hover:border-primary/40 hover:bg-muted/50'
            )}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,application/pdf"
              multiple
              className="sr-only"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <div
              className={cn(
                'size-14 rounded-2xl flex items-center justify-center transition-colors',
                isDragging ? 'bg-primary/20' : 'bg-muted'
              )}
            >
              <CloudUpload
                className={cn('size-7 transition-colors', isDragging ? 'text-primary' : 'text-muted-foreground')}
              />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-foreground mb-1">
                {isDragging ? 'Drop to upload' : 'Upload PDF documents'}
              </p>
              <p className="text-xs text-muted-foreground">
                Drag & drop or click to browse · PDF only
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={(e) => {
                e.stopPropagation()
                inputRef.current?.click()
              }}
              className="text-xs h-7"
            >
              Choose files
            </Button>
          </div>

          {/* Info */}
          <div className="rounded-xl bg-muted/50 border border-border p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { label: 'Supported format', value: 'PDF only' },
              { label: 'Processing', value: 'Semantic chunking' },
              { label: 'Storage', value: 'ChromaDB vectors' },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">{label}</p>
                <p className="text-xs text-foreground font-medium">{value}</p>
              </div>
            ))}
          </div>

          {/* File history */}
          {files.length > 0 && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                  Session uploads
                </p>
                <button
                  onClick={() => setFiles([])}
                  className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  Clear all
                </button>
              </div>
              <div className="flex flex-col gap-2">
                {files.map((file) => (
                  <FileCard key={file.id} file={file} onRemove={removeFile} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function FileCard({ file, onRemove }: { file: UploadedFile; onRemove: (id: string) => void }) {
  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-xl border p-3 transition-colors',
        file.status === 'success'
          ? 'border-emerald-500/20 bg-emerald-500/5'
          : file.status === 'error'
          ? 'border-destructive/20 bg-destructive/5'
          : 'border-border bg-card'
      )}
    >
      <div className="mt-0.5 shrink-0">
        {file.status === 'uploading' ? (
          <Loader2 className="size-4 text-primary animate-spin" />
        ) : file.status === 'success' ? (
          <CheckCircle2 className="size-4 text-emerald-500" />
        ) : (
          <XCircle className="size-4 text-destructive" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <FileText className="size-3 text-muted-foreground shrink-0" />
          <span className="text-xs font-medium text-foreground truncate">{file.filename}</span>
        </div>
        {file.message && (
          <p
            className={cn(
              'text-[11px] mt-0.5 leading-relaxed',
              file.status === 'error' ? 'text-destructive' : 'text-muted-foreground'
            )}
          >
            {file.status === 'uploading' ? 'Processing…' : file.message}
          </p>
        )}
        {file.status === 'uploading' && !file.message && (
          <p className="text-[11px] mt-0.5 text-muted-foreground">Uploading and embedding…</p>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {file.chunks !== undefined && (
          <Badge
            variant="secondary"
            className="text-[10px] px-1.5 py-0 h-4 bg-primary/10 text-primary border-0"
          >
            {file.chunks} chunks
          </Badge>
        )}
        {file.status !== 'uploading' && (
          <button
            onClick={() => onRemove(file.id)}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="size-3" />
          </button>
        )}
      </div>
    </div>
  )
}
