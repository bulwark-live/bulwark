import { useRef, useEffect, useState } from 'react'
import { useEvents } from '../api/client'
import { Search, Code, Cpu, FileText, Play, Square } from 'lucide-react'
import type { Event } from '../types'

const eventIcons: Record<string, typeof Search> = {
  tool_call: Code,
  llm_call: Cpu,
  action: FileText,
  session_start: Play,
  session_end: Square,
}

const statusColors: Record<string, string> = {
  success: 'text-green-400',
  failure: 'text-red-400',
  error: 'text-red-400',
  killed: 'text-red-500',
  blocked: 'text-orange-400',
}

function eventSummary(e: Event): string {
  const p = e.payload as Record<string, unknown>
  switch (e.event_type) {
    case 'tool_call':
      return `${p.tool_name || 'unknown'}`
    case 'llm_call':
      return `${p.model || 'unknown'} (${p.input_tokens || 0}→${p.output_tokens || 0} tokens)`
    case 'action':
      return `${p.action || 'unknown'} → ${p.target || ''}`
    case 'session_start':
      return `Session started (${p.framework || 'manual'})`
    case 'session_end':
      return `Session ended (${p.total_events || 0} events)`
    default:
      return e.event_type
  }
}

function formatTime(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function EventFeed() {
  const { data } = useEvents()
  const events = data?.events ?? []
  const feedRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  useEffect(() => {
    if (autoScroll && feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [events, autoScroll])

  function handleScroll() {
    if (!feedRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = feedRef.current
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 50)
  }

  return (
    <div className="flex flex-col flex-1">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">
          Live Event Feed
        </h2>
        {!autoScroll && (
          <button
            onClick={() => setAutoScroll(true)}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            Resume auto-scroll
          </button>
        )}
      </div>

      <div
        ref={feedRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto bg-gray-900 border border-gray-800 rounded-lg font-mono text-sm"
      >
        {events.length === 0 && (
          <div className="p-8 text-center text-gray-600">
            No events yet. Start an agent to see activity.
          </div>
        )}
        {events.map(e => {
          const Icon = eventIcons[e.event_type] || FileText
          const color = statusColors[e.status] || 'text-gray-400'
          return (
            <div
              key={e.id}
              className="flex items-start gap-3 px-4 py-2 border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
            >
              <span className="text-xs text-gray-600 whitespace-nowrap mt-0.5">
                {formatTime(e.timestamp)}
              </span>
              <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${color}`} />
              <div className="flex-1 min-w-0">
                <span className={`${color}`}>{eventSummary(e)}</span>
                {e.duration_ms != null && (
                  <span className="text-gray-600 ml-2">{e.duration_ms}ms</span>
                )}
              </div>
              <span className="text-xs text-gray-700 font-mono truncate max-w-24">
                {e.session_id}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
