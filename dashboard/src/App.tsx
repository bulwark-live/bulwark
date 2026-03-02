import { useState } from 'react'
import { Layout } from './components/Layout'
import { AgentSidebar } from './components/AgentSidebar'
import { EventFeed } from './components/EventFeed'
import { SessionTimeline } from './components/SessionTimeline'
import { StatsStrip } from './components/StatsStrip'
import { KillButton } from './components/KillButton'
import { AlertBell } from './components/AlertBell'
import { RulesPanel } from './components/RulesPanel'
import { ApiKeyPrompt } from './components/ApiKeyPrompt'
import { getApiKey } from './api/client'

type View = 'feed' | 'rules'

export default function App() {
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [view, setView] = useState<View>('feed')

  if (!getApiKey()) {
    return <ApiKeyPrompt />
  }

  return (
    <Layout
      sidebar={
        <AgentSidebar
          selectedSession={selectedSession}
          onSelectSession={(id) => {
            setSelectedSession(id)
            setView('feed')
          }}
        />
      }
      topRight={
        <div className="flex items-center gap-2">
          <AlertBell onSelectSession={(id) => {
            setSelectedSession(id)
            setView('feed')
          }} />
          <KillButton selectedSession={selectedSession} />
        </div>
      }
    >
      <StatsStrip />
      {selectedSession ? (
        <SessionTimeline
          sessionId={selectedSession}
          onBack={() => setSelectedSession(null)}
        />
      ) : (
        <>
          <div className="flex items-center gap-1 mb-4 border-b border-gray-800">
            <button
              onClick={() => setView('feed')}
              className={`px-3 py-2 text-sm font-medium transition-colors ${
                view === 'feed'
                  ? 'text-gray-100 border-b-2 border-red-500'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Live Feed
            </button>
            <button
              onClick={() => setView('rules')}
              className={`px-3 py-2 text-sm font-medium transition-colors ${
                view === 'rules'
                  ? 'text-gray-100 border-b-2 border-red-500'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Alert Rules
            </button>
          </div>
          {view === 'feed' ? <EventFeed /> : <RulesPanel />}
        </>
      )}
    </Layout>
  )
}
