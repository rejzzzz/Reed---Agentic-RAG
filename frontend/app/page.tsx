'use client'

import { useState, useEffect, useCallback } from 'react'
import { AppSidebar, type ActiveView } from '@/components/app-sidebar'
import { ChatView } from '@/components/chat-view'
import { UploadView } from '@/components/upload-view'
import { LibraryView } from '@/components/library-view'
import { SettingsView } from '@/components/settings-view'
import { checkHealth, fetchProviders } from '@/lib/api'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export default function ReedApp() {
  const [activeView, setActiveView] = useState<ActiveView>('chat')
  const [isOnline, setIsOnline] = useState<boolean | null>(null)
  const [providers, setProviders] = useState<string[]>([])
  const [isCheckingHealth, setIsCheckingHealth] = useState(false)

  const doHealthCheck = useCallback(async () => {
    setIsCheckingHealth(true)
    try {
      await checkHealth()
      setIsOnline(true)
    } catch {
      setIsOnline(false)
    } finally {
      setIsCheckingHealth(false)
    }
  }, [])

  const loadProviders = useCallback(async () => {
    try {
      const res = await fetchProviders()
      setProviders(res.available_providers)
    } catch {
      // silently fail — providers just won't be populated
    }
  }, [])

  useEffect(() => {
    doHealthCheck()
    loadProviders()
  }, [doHealthCheck, loadProviders])

  const handleUploadSuccess = (filename: string) => {
    // Optionally trigger a refresh or notification
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AppSidebar
        activeView={activeView}
        onViewChange={setActiveView}
        isOnline={isOnline}
      />

      <main className="flex-1 min-w-0 overflow-hidden">
        {activeView === 'chat' && (
          <ChatView providers={providers} defaultProvider={providers[0]} />
        )}
        {activeView === 'upload' && (
          <UploadView onUploadSuccess={handleUploadSuccess} />
        )}
        {activeView === 'library' && (
          <LibraryView onViewChange={setActiveView} />
        )}
        {activeView === 'settings' && (
          <SettingsView
            isOnline={isOnline}
            providers={providers}
            onRefreshHealth={doHealthCheck}
            isCheckingHealth={isCheckingHealth}
            baseUrl={BASE_URL}
          />
        )}
      </main>
    </div>
  )
}
