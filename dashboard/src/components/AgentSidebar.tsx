import { useSessions } from '../api/client'
import { Activity, Skull, CircleStop, Circle } from 'lucide-react'
import type { SessionSummary } from '../types'

interface AgentSidebarProps {
  selectedSession: string | null
  onSelectSession: (id: string | null) => void
}

function sessionStatus(s: SessionSummary): { label: string; color: string; icon: typeof Activity } {
  if (s.killed_at) return { label: 'KILLED', color: 'text-red-500', icon: Skull }
  if (s.ended_at) return { label: 'ENDED', color: 'text-gray-500', icon: CircleStop }
  return { label: 'ACTIVE', color: 'text-green-500', icon: Activity }
}

export function AgentSidebar({ selectedSession, onSelectSession }: AgentSidebarProps) {
  const { data, isLoading } = useSessions()
  const sessions = data?.sessions ?? []

  // Group sessions by active vs ended
  const active = sessions.filter(s => !s.ended_at && !s.killed_at)
  const inactive = sessions.filter(s => s.ended_at || s.killed_at)

  return (
    <div className="p-3">
      {/* Live indicator */}
      <div className="flex items-center gap-2 px-2 py-1 mb-3">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
        </span>
        <span className="text-xs text-gray-400 uppercase tracking-wider font-medium">
          Live Sessions ({active.length})
        </span>
      </div>

      {isLoading && (
        <div className="text-xs text-gray-500 px-2">Loading...</div>
      )}

      {/* Active sessions */}
      {active.map(s => {
        const st = sessionStatus(s)
        const Icon = st.icon
        return (
          <button
            key={s.id}
            onClick={() => onSelectSession(selectedSession === s.id ? null : s.id)}
            className={`w-full text-left px-3 py-2 rounded-lg mb-1 transition-colors ${
              selectedSession === s.id
                ? 'bg-gray-800 border border-gray-700'
                : 'hover:bg-gray-900'
            }`}
          >
            <div className="flex items-center gap-2">
              <Icon className={`w-3.5 h-3.5 ${st.color}`} />
              <span className="text-sm font-mono truncate">{s.id}</span>
            </div>
            <div className="flex items-center gap-2 mt-1 ml-5.5">
              <span className="text-xs text-gray-500">{s.agent_name}</span>
              <span className="text-xs text-gray-600">|</span>
              <span className="text-xs text-gray-500">{s.event_count} events</span>
            </div>
          </button>
        )
      })}

      {/* Past sessions */}
      {inactive.length > 0 && (
        <>
          <div className="flex items-center gap-2 px-2 py-1 mt-4 mb-2">
            <Circle className="w-2 h-2 text-gray-600" />
            <span className="text-xs text-gray-500 uppercase tracking-wider font-medium">
              Past Sessions ({inactive.length})
            </span>
          </div>
          {inactive.map(s => {
            const st = sessionStatus(s)
            const Icon = st.icon
            return (
              <button
                key={s.id}
                onClick={() => onSelectSession(selectedSession === s.id ? null : s.id)}
                className={`w-full text-left px-3 py-2 rounded-lg mb-1 transition-colors ${
                  selectedSession === s.id
                    ? 'bg-gray-800 border border-gray-700'
                    : 'hover:bg-gray-900'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon className={`w-3.5 h-3.5 ${st.color}`} />
                  <span className="text-sm font-mono truncate">{s.id}</span>
                </div>
                <div className="flex items-center gap-2 mt-1 ml-5.5">
                  <span className="text-xs text-gray-500">{s.agent_name}</span>
                  <span className={`text-xs ${st.color}`}>{st.label}</span>
                </div>
              </button>
            )
          })}
        </>
      )}
    </div>
  )
}
