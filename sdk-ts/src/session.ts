/**
 * Session context for Bulwark monitoring.
 *
 * Tracks tool calls, LLM calls, and actions within a session.
 * Polls the kill switch in the background.
 *
 * @example
 * ```ts
 * const session = bulwark.session('my-task')
 * await session.start()
 *
 * session.trackToolCall({ tool: 'search', input: { q: 'hello' } })
 *
 * if (session.isKilled) {
 *   console.log('Agent killed!')
 * }
 *
 * await session.end()
 * ```
 */

import { BulwarkClient } from './client'
import type { TrackToolCallOptions, TrackLlmCallOptions, TrackActionOptions, BaseEvent } from './types'

let idCounter = 0

function generateSessionId(): string {
  const hex = Math.random().toString(16).slice(2, 14).padEnd(12, '0')
  return `ses_${hex}`
}

export class Session {
  readonly client: BulwarkClient
  readonly sessionId: string
  readonly name: string | undefined

  private _startTime = 0
  private _eventCount = 0
  private _killed = false
  private _killTimer: ReturnType<typeof setInterval> | null = null

  constructor(client: BulwarkClient, name?: string) {
    this.client = client
    this.sessionId = generateSessionId()
    this.name = name
  }

  /** Whether a kill signal has been received. */
  get isKilled(): boolean {
    return this._killed
  }

  /** Number of events tracked in this session. */
  get eventCount(): number {
    return this._eventCount
  }

  /** Start the session — sends start event and begins kill switch polling. */
  async start(): Promise<void> {
    this._startTime = Date.now()
    try {
      this.client.sendEvent(this._event('session_start', {
        sdk_version: '0.1.0',
        runtime: `node/${process.version}`,
      }))
    } catch {
      // Never crash the host
    }
    this._startKillPolling()
  }

  /** End the session — sends end event and stops kill switch polling. */
  async end(status?: 'success' | 'error' | 'killed'): Promise<void> {
    try {
      const elapsed = Date.now() - this._startTime
      const finalStatus = status ?? (this._killed ? 'killed' : 'success')
      this.client.sendEvent(this._event('session_end', {
        total_events: this._eventCount,
        total_duration_ms: elapsed,
        status: finalStatus,
      }))
      await this.client.flush()
    } catch {
      // Never crash the host
    }
    this._stopKillPolling()
  }

  /**
   * Track an agent tool call. Never throws.
   *
   * @example
   * ```ts
   * session.trackToolCall({
   *   tool: 'search_web',
   *   input: { query: 'latest news' },
   *   output: { results: 10 },
   *   durationMs: 350,
   * })
   * ```
   */
  trackToolCall(opts: TrackToolCallOptions): void {
    try {
      this._eventCount++
      this.client.sendEvent(this._event('tool_call', {
        tool_name: opts.tool,
        tool_input: opts.input,
        tool_output: opts.output,
        duration_ms: opts.durationMs,
        status: opts.status ?? 'success',
      }))
    } catch {
      console.warn('bulwark: failed to track tool call')
    }
  }

  /**
   * Track an LLM API call. Never throws.
   *
   * @example
   * ```ts
   * session.trackLlmCall({
   *   model: 'claude-sonnet-4-6',
   *   inputTokens: 1200,
   *   outputTokens: 400,
   *   costUsd: 0.005,
   *   provider: 'anthropic',
   * })
   * ```
   */
  trackLlmCall(opts: TrackLlmCallOptions): void {
    try {
      this._eventCount++
      this.client.sendEvent(this._event('llm_call', {
        model: opts.model,
        provider: opts.provider ?? '',
        input_tokens: opts.inputTokens ?? 0,
        output_tokens: opts.outputTokens ?? 0,
        cost_usd: opts.costUsd ?? 0,
        prompt_summary: opts.promptSummary ?? '',
        duration_ms: opts.durationMs,
      }))
    } catch {
      console.warn('bulwark: failed to track LLM call')
    }
  }

  /**
   * Track a generic agent action. Never throws.
   *
   * @example
   * ```ts
   * session.trackAction({
   *   action: 'send_email',
   *   target: 'user@example.com',
   *   metadata: { subject: 'Weekly Report' },
   * })
   * ```
   */
  trackAction(opts: TrackActionOptions): void {
    try {
      this._eventCount++
      this.client.sendEvent(this._event('action', {
        action: opts.action,
        target: opts.target ?? '',
        metadata: opts.metadata ?? {},
        duration_ms: opts.durationMs,
        status: opts.status ?? 'success',
      }))
    } catch {
      console.warn('bulwark: failed to track action')
    }
  }

  private _event(type: string, data: Record<string, unknown>): BaseEvent {
    return {
      event_type: type,
      session_id: this.sessionId,
      agent_name: this.client.agentName,
      environment: this.client.environment,
      timestamp: new Date().toISOString(),
      ...data,
    }
  }

  private _startKillPolling(): void {
    this._killTimer = setInterval(async () => {
      try {
        this._killed = await this.client.checkKill(this.sessionId)
      } catch {
        // Fail-open
      }
    }, this.client.killCheckIntervalMs)
  }

  private _stopKillPolling(): void {
    if (this._killTimer) {
      clearInterval(this._killTimer)
      this._killTimer = null
    }
  }
}
