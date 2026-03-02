import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Agent, SessionSummary, Event, Stats } from '../types'

const API_KEY = localStorage.getItem('bulwark_api_key') || ''

const headers = () => ({
  'Authorization': `Bearer ${API_KEY}`,
  'Content-Type': 'application/json',
})

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: headers() })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

// Agents
export function useAgents() {
  return useQuery<{ agents: Agent[] }>({
    queryKey: ['agents'],
    queryFn: () => fetchJSON('/v1/agents'),
    refetchInterval: 3000,
  })
}

// Sessions
export function useSessions() {
  return useQuery<{ sessions: SessionSummary[] }>({
    queryKey: ['sessions'],
    queryFn: () => fetchJSON('/v1/sessions'),
    refetchInterval: 2000,
  })
}

// Session detail
export function useSession(sessionId: string | null) {
  return useQuery<{ session: SessionSummary; events: Event[] }>({
    queryKey: ['session', sessionId],
    queryFn: () => fetchJSON(`/v1/sessions/${sessionId}`),
    enabled: !!sessionId,
    refetchInterval: 2000,
  })
}

// Events feed
export function useEvents(since?: string) {
  const params = new URLSearchParams({ limit: '100' })
  if (since) params.set('since', since)
  return useQuery<{ events: Event[] }>({
    queryKey: ['events', since],
    queryFn: () => fetchJSON(`/v1/events?${params}`),
    refetchInterval: 2000,
  })
}

// Stats
export function useStats() {
  return useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: () => fetchJSON('/v1/stats'),
    refetchInterval: 3000,
  })
}

// Kill session
export function useKillSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const res = await fetch(`/v1/sessions/${sessionId}/kill`, {
        method: 'POST',
        headers: headers(),
      })
      if (!res.ok) throw new Error(`Kill failed: ${res.status}`)
      return res.json()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sessions'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

// Alert Rules
export interface AlertRule {
  id: string
  name: string
  description: string
  enabled: boolean
  condition: { metric: string; operator: string; threshold: number; window_seconds: number }
  actions: { type: string; url?: string }[]
  cooldown_seconds: number
  created_at: string
  updated_at: string
}

export interface AlertRecord {
  id: string
  rule_id: string
  rule_name: string
  session_id: string
  metric_value: number
  threshold: number
  actions_taken: string[]
  acknowledged: boolean
  created_at: string
}

export function useAlertRules() {
  return useQuery<{ rules: AlertRule[] }>({
    queryKey: ['rules'],
    queryFn: () => fetchJSON('/v1/rules'),
    refetchInterval: 5000,
  })
}

export function useAlerts() {
  return useQuery<{ alerts: AlertRecord[] }>({
    queryKey: ['alerts'],
    queryFn: () => fetchJSON('/v1/alerts'),
    refetchInterval: 3000,
  })
}

export function useUnreadAlerts() {
  return useQuery<{ unread: number }>({
    queryKey: ['alerts', 'unread'],
    queryFn: () => fetchJSON('/v1/alerts/unread'),
    refetchInterval: 3000,
  })
}

export function useToggleRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (ruleId: string) => {
      const res = await fetch(`/v1/rules/${ruleId}/toggle`, {
        method: 'POST',
        headers: headers(),
      })
      if (!res.ok) throw new Error(`Toggle failed: ${res.status}`)
      return res.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rules'] }),
  })
}

export function useAcknowledgeAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (alertId: string) => {
      const res = await fetch(`/v1/alerts/${alertId}/ack`, {
        method: 'POST',
        headers: headers(),
      })
      if (!res.ok) throw new Error(`Ack failed: ${res.status}`)
      return res.json()
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })
}

export function useCreateRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (rule: Omit<AlertRule, 'id' | 'created_at' | 'updated_at'>) => {
      const res = await fetch('/v1/rules', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(rule),
      })
      if (!res.ok) throw new Error(`Create failed: ${res.status}`)
      return res.json()
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rules'] }),
  })
}

// API key management
export function setApiKey(key: string) {
  localStorage.setItem('bulwark_api_key', key)
  window.location.reload()
}

export function getApiKey(): string {
  return localStorage.getItem('bulwark_api_key') || ''
}
