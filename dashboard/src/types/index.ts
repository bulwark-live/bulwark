export interface Agent {
  id: string
  name: string
  active_sessions: number
  total_events_24h: number
  total_cost_24h: number
}

export interface SessionSummary {
  id: string
  agent_name: string
  environment: string
  started_at: string
  ended_at: string | null
  killed_at: string | null
  event_count: number
}

export interface Event {
  id: string
  session_id: string
  event_type: 'tool_call' | 'llm_call' | 'action' | 'session_start' | 'session_end'
  timestamp: string
  duration_ms: number | null
  status: string
  payload: Record<string, unknown>
}

export interface Stats {
  active_sessions: number
  total_agents: number
  events_per_minute: number
  cost_24h: number
}
