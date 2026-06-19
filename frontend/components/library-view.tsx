'use client'

import { useState, useEffect, useCallback } from 'react'
import { BookOpen, FileText, Clock, Upload, Trash2, Loader2, Layers } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { fetchDocuments, deleteDocument, type DocumentItem } from '@/lib/api'
import type { ActiveView } from './app-sidebar'

interface LibraryViewProps {
  onViewChange: (view: ActiveView) => void
}

export function LibraryView({ onViewChange }: LibraryViewProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [totalChunks, setTotalChunks] = useState(0)
  const [loading, setLoading] = useState(true)
  const [deletingFile, setDeletingFile] = useState<string | null>(null)

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchDocuments()
      setDocuments(res.documents)
      setTotalChunks(res.total_chunks)
    } catch (err) {
      console.error('Failed to load documents', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleDelete = async (filename: string) => {
    setDeletingFile(filename)
    try {
      await deleteDocument(filename)
      await loadDocuments()
    } catch (err) {
      console.error('Failed to delete document', err)
    } finally {
      setDeletingFile(null)
    }
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="flex items-center justify-between px-4 lg:px-6 h-14 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <BookOpen className="size-4 text-primary" />
          <h1 className="text-sm font-semibold text-foreground">Knowledge Base</h1>
        </div>
        {!loading && documents.length > 0 && (
          <div className="flex gap-2">
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 bg-primary/10 text-primary border-0">
              {documents.length} docs
            </Badge>
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 bg-emerald-500/10 text-emerald-500 border-0">
              {totalChunks} chunks
            </Badge>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto p-4 lg:p-6">
        <div className="max-w-2xl mx-auto flex flex-col gap-4">
          {loading ? (
            <div className="flex justify-center items-center py-20">
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            </div>
          ) : documents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <div className="size-14 rounded-2xl bg-muted flex items-center justify-center">
                <BookOpen className="size-6 text-muted-foreground" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground mb-1">No documents yet</p>
                <p className="text-xs text-muted-foreground max-w-xs text-balance">
                  Upload PDF documents to start building your knowledge base.
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onViewChange('upload')}
                className="text-xs h-7 gap-1.5"
              >
                <Upload className="size-3" />
                Upload a document
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mb-1">
                Indexed documents
              </p>
              {documents.map((doc, i) => (
                <div
                  key={`${doc.filename}-${i}`}
                  className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 group transition-colors hover:border-primary/50"
                >
                  <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <FileText className="size-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-foreground truncate">{doc.filename}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <div className="flex items-center gap-1">
                        <Layers className="size-3 text-muted-foreground" />
                        <p className="text-[10px] text-muted-foreground">{doc.chunk_count} chunks</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="size-3 text-muted-foreground" />
                        <p className="text-[10px] text-muted-foreground">Indexed in ChromaDB</p>
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => handleDelete(doc.filename)}
                    disabled={deletingFile === doc.filename}
                  >
                    {deletingFile === doc.filename ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="size-3.5" />
                    )}
                  </Button>
                </div>
              ))}

              <div className="mt-2 text-center">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onViewChange('upload')}
                  className="text-xs h-7 gap-1.5"
                >
                  <Upload className="size-3" />
                  Upload more
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
