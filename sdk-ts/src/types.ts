/** Configuration for initializing the Bulwark SDK. */
export interface BulwarkConfig {
  /** Your Bulwark API key (starts with `bwk_`). */
  apiKey: string
  /** Name identifying this agent (e.g. "research-agent"). */
  agentName: string
  /** Deployment environment. Default "production". */
  environment?: string
  /** If true, strip tool inputs before sending to API. */
  redactInputs?: boolean
  /** If true, strip tool outputs before sending to API. */
  redactOutputs?: boolean
  /** Bulwark API URL. Default "https://api.bulwark.live". */
  endpoint?: string
  /** How often to flush buffered events in ms. Default 1000. */
  flushIntervalMs?: number
  /** How often sessions poll the kill switch in ms. Default 10000. */
  killCheckIntervalMs?: number
}

/** Base event shape sent to the API. */
export interface BaseEvent {
  event_type: string
  session_id: string
  agent_name: string
  environment: string
  timestamp: string
  [key: string]: unknown
}

/** Options for tracking a tool call. */
export interface TrackToolCallOptions {
  tool: string
  input?: unknown
  output?: unknown
  durationMs?: number
  status?: 'success' | 'error'
}

/** Options for tracking an LLM call. */
export interface TrackLlmCallOptions {
  model: string
  inputTokens?: number
  outputTokens?: number
  costUsd?: number
  provider?: string
  promptSummary?: string
  durationMs?: number
}

/** Options for tracking a generic action. */
export interface TrackActionOptions {
  action: string
  target?: string
  metadata?: Record<string, unknown>
  durationMs?: number
  status?: 'success' | 'error'
}
