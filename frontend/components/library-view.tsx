'use client'

import { BookOpen, FileText, Clock, Upload, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { ActiveView } from './app-sidebar'

interface LibraryViewProps {
  uploadedFiles: string[]
  onViewChange: (view: ActiveView) => void
}

export function LibraryView({ uploadedFiles, onViewChange }: LibraryViewProps) {
  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="flex items-center justify-between px-4 lg:px-6 h-14 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <BookOpen className="size-4 text-primary" />
          <h1 className="text-sm font-semibold text-foreground">Knowledge Base</h1>
        </div>
        {uploadedFiles.length > 0 && (
          <Badge
            variant="secondary"
            className="text-[10px] px-1.5 py-0 h-4 bg-primary/10 text-primary border-0"
          >
            {uploadedFiles.length} indexed
          </Badge>
        )}
      </div>

      <div className="flex-1 overflow-auto p-4 lg:p-6">
        <div className="max-w-2xl mx-auto flex flex-col gap-4">
          {/* Coming soon notice */}
          <div className="flex items-start gap-3 rounded-xl border border-border bg-muted/30 p-4">
            <Info className="size-4 text-primary shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-foreground mb-0.5">
                Document management coming soon
              </p>
              <p className="text-xs text-muted-foreground leading-relaxed">
                The backend API for listing and deleting indexed documents is in development. 
                Files uploaded this session are shown below.
              </p>
            </div>
          </div>

          {uploadedFiles.length === 0 ? (
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
                Session documents — {uploadedFiles.length} file{uploadedFiles.length !== 1 ? 's' : ''}
              </p>
              {uploadedFiles.map((filename, i) => (
                <div
                  key={`${filename}-${i}`}
                  className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3"
                >
                  <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <FileText className="size-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-foreground truncate">{filename}</p>
                    <div className="flex items-center gap-1 mt-0.5">
                      <Clock className="size-2.5 text-muted-foreground" />
                      <p className="text-[10px] text-muted-foreground">Indexed this session</p>
                    </div>
                  </div>
                  <Badge
                    variant="secondary"
                    className="text-[10px] px-1.5 py-0 h-4 bg-emerald-500/10 text-emerald-400 border-0 shrink-0"
                  >
                    indexed
                  </Badge>
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
