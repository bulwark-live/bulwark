import { useState } from 'react'
import { useSession } from '../api/client'
import { ArrowLeft, ChevronDown, ChevronRight, Download, Code, Cpu, FileText, Play, Square, Skull } from 'lucide-react'
import type { Event } from '../types'

const eventIcons: Record<string, typeof Code> = {
  tool_call: Code,
  llm_call: Cpu,
  action: FileText,
  session_start: Play,
  session_end: Square,
}

const statusColors: Record<string, string> = {
  success: 'border-green-600 bg-green-950/30',
  failure: 'border-red-600 bg-red-950/30',
  error: 'border-red-600 bg-red-950/30',
  killed: 'border-red-500 bg-red-950/50',
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 })
}

function EventNode({ event }: { event: Event }) {
  const [expanded, setExpanded] = useState(false)
  const Icon = eventIcons[event.event_type] || FileText
  const p = event.payload as Record<string, unknown>
  const color = statusColors[event.status] || 'border-gray-700 bg-gray-900'

  let title: string = event.event_type
  let detail = ''
  switch (event.event_type) {
    case 'tool_call':
      title = `tool_call: ${p.tool_name || 'unknown'}`
      detail = p.tool_input ? `Input: ${JSON.stringify(p.tool_input)}` : ''
      break
    case 'llm_call':
      title = `llm_call: ${p.model || 'unknown'}`
      detail = `Tokens: ${p.input_tokens || 0} in / ${p.output_tokens || 0} out | Cost: $${(p.cost_usd as number || 0).toFixed(4)}`
      break
    case 'action':
      title = `action: ${p.action || 'unknown'}`
      detail = p.target ? `Target: ${p.target}` : ''
      break
    case 'session_start':
      title = 'Session Started'
      detail = `SDK: ${p.sdk_version || '-'} | Python: ${p.python_version || '-'} | Framework: ${p.framework || 'manual'}`
      break
    case 'session_end':
      title = 'Session Ended'
      detail = `Total events: ${p.total_events || 0} | Duration: ${p.total_duration_ms || 0}ms`
      break
  }

  return (
    <div className="flex gap-3 mb-1">
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center border ${color}`}>
          {event.status === 'killed' ? (
            <Skull className="w-4 h-4 text-red-500" />
          ) : (
            <Icon className="w-4 h-4 text-gray-300" />
          )}
        </div>
        <div className="w-px flex-1 bg-gray-800 mt-1"></div>
      </div>

      {/* Content */}
      <div className="flex-1 pb-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-left w-full group"
        >
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
          )}
          <span className="text-xs text-gray-500 font-mono">{formatTimestamp(event.timestamp)}</span>
          <span className="text-sm font-medium text-gray-200 group-hover:text-white">{title}</span>
          {event.duration_ms != null && (
            <span className="text-xs text-gray-600">{event.duration_ms}ms</span>
          )}
          <span className={`text-xs px-1.5 py-0.5 rounded ${
            event.status === 'success' ? 'bg-green-950 text-green-400' :
            event.status === 'killed' ? 'bg-red-950 text-red-400' :
            'bg-red-950 text-red-400'
          }`}>
            {event.status}
          </span>
        </button>

        {detail && (
          <div className="text-xs text-gray-500 mt-1 ml-5">{detail}</div>
        )}

        {expanded && (
          <div className="mt-2 ml-5 bg-gray-900 border border-gray-800 rounded-lg p-3 overflow-x-auto">
            <pre className="text-xs text-gray-400 whitespace-pre-wrap">
              {JSON.stringify(event.payload, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

interface SessionTimelineProps {
  sessionId: string
  onBack: () => void
}

export function SessionTimeline({ sessionId, onBack }: SessionTimelineProps) {
  const { data, isLoading } = useSession(sessionId)

  function exportJSON() {
    if (!data) return
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bulwark-session-${sessionId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const session = data?.session
  const events = data?.events ?? []

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-1.5 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-gray-400" />
          </button>
          <div>
            <h2 className="text-sm font-medium text-gray-200">
              Session <span className="font-mono">{sessionId}</span>
            </h2>
            {session && (
              <div className="flex items-center gap-2 mt-0.5">
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  session.killed_at ? 'bg-red-950 text-red-400' :
                  session.ended_at ? 'bg-gray-800 text-gray-400' :
                  'bg-green-950 text-green-400'
                }`}>
                  {session.killed_at ? 'KILLED' : session.ended_at ? 'ENDED' : 'ACTIVE'}
                </span>
                <span className="text-xs text-gray-500">{events.length} events</span>
              </div>
            )}
          </div>
        </div>

        <button
          onClick={exportJSON}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 px-3 py-1.5 border border-gray-700 rounded-lg hover:border-gray-600 transition-colors"
        >
          <Download className="w-3.5 h-3.5" />
          Export JSON
        </button>
      </div>

      {/* Timeline */}
      {isLoading ? (
        <div className="text-gray-500 text-sm">Loading session...</div>
      ) : (
        <div className="ml-2">
          {events.map(e => (
            <EventNode key={e.id} event={e} />
          ))}
        </div>
      )}
    </div>
  )
}
