'use client'

import { MessageSquare, Upload, BookOpen, Settings, Activity, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

export type ActiveView = 'chat' | 'upload' | 'library' | 'settings'

interface AppSidebarProps {
  activeView: ActiveView
  onViewChange: (view: ActiveView) => void
  isOnline: boolean | null
}

const navItems = [
  { id: 'chat' as ActiveView, label: 'Chat', icon: MessageSquare },
  { id: 'upload' as ActiveView, label: 'Upload', icon: Upload },
  { id: 'library' as ActiveView, label: 'Library', icon: BookOpen },
  { id: 'settings' as ActiveView, label: 'Settings', icon: Settings },
]

export function AppSidebar({ activeView, onViewChange, isOnline }: AppSidebarProps) {
  return (
    <aside className="flex flex-col w-14 lg:w-56 shrink-0 border-r border-border bg-sidebar h-screen sticky top-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-3 lg:px-4 h-14 border-b border-border">
        <div className="size-7 rounded-md bg-primary flex items-center justify-center shrink-0">
          <span className="text-primary-foreground font-bold text-sm font-mono">R</span>
        </div>
        <span className="hidden lg:block text-foreground font-semibold tracking-tight text-[15px]">
          Reed
        </span>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1 p-2 flex-1">
        {navItems.map(({ id, label, icon: Icon }) => (
          <Tooltip key={id}>
            <TooltipTrigger
              onClick={() => onViewChange(id)}
              className={cn(
                'flex items-center gap-3 px-2 lg:px-3 h-9 rounded-md text-sm transition-colors w-full',
                activeView === id
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              )}
            >
              <Icon className="size-4 shrink-0" />
              <span className="hidden lg:block">{label}</span>
              {activeView === id && (
                <ChevronRight className="hidden lg:block ml-auto size-3 text-muted-foreground" />
              )}
            </TooltipTrigger>
            <TooltipContent side="right" className="lg:hidden">
              {label}
            </TooltipContent>
          </Tooltip>
        ))}
      </nav>

      {/* Status */}
      <div className="p-3 border-t border-border">
        <Tooltip>
          <TooltipTrigger className="flex items-center gap-2 px-2 lg:px-3 h-8 rounded-md cursor-default w-full text-left outline-none border-none bg-transparent">
            <Activity className="size-3.5 shrink-0 text-muted-foreground" />
            <div className="hidden lg:flex items-center gap-2 flex-1 min-w-0">
              <span className="text-xs text-muted-foreground truncate">API</span>
              <div
                className={cn(
                  'size-1.5 rounded-full ml-auto shrink-0',
                  isOnline === null
                    ? 'bg-muted-foreground'
                    : isOnline
                    ? 'bg-emerald-500'
                    : 'bg-destructive'
                )}
              />
            </div>
          </TooltipTrigger>
          <TooltipContent side="right">
            {isOnline === null ? 'Checking…' : isOnline ? 'API online' : 'API offline'}
          </TooltipContent>
        </Tooltip>
      </div>
    </aside>
  )
}
