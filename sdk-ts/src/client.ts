/**
 * HTTP client for Bulwark API.
 *
 * Designed to never crash the host agent. All failures are handled gracefully
 * with logging, retries, and degraded mode fallbacks.
 */

import type { BaseEvent } from './types'

const MAX_BUFFER_SIZE = 1000
const MAX_RETRY_ATTEMPTS = 3
const RETRY_BACKOFF_BASE = 1000 // ms
const CONNECT_TIMEOUT = 5000
const READ_TIMEOUT = 10000

export class BulwarkClient {
  readonly apiKey: string
  readonly agentName: string
  readonly environment: string
  readonly endpoint: string
  readonly redactInputs: boolean
  readonly redactOutputs: boolean
  readonly flushIntervalMs: number
  readonly killCheckIntervalMs: number

  private _buffer: Record<string, unknown>[] = []
  private _healthy = true
  private _droppedEvents = 0
  private _flushTimer: ReturnType<typeof setInterval> | null = null
  private _running = true

  constructor(opts: {
    apiKey: string
    agentName: string
    environment: string
    endpoint: string
    redactInputs: boolean
    redactOutputs: boolean
    flushIntervalMs: number
    killCheckIntervalMs: number
  }) {
    this.apiKey = opts.apiKey
    this.agentName = opts.agentName
    this.environment = opts.environment
    this.endpoint = opts.endpoint.replace(/\/+$/, '')
    this.redactInputs = opts.redactInputs
    this.redactOutputs = opts.redactOutputs
    this.flushIntervalMs = opts.flushIntervalMs
    this.killCheckIntervalMs = opts.killCheckIntervalMs

    // Start background flush
    this._flushTimer = setInterval(() => {
      this.flush().catch(() => {})
    }, this.flushIntervalMs)
  }

  /** True when the API connection is working normally. */
  get isHealthy(): boolean {
    return this._healthy
  }

  /** Number of events currently buffered. */
  get bufferSize(): number {
    return this._buffer.length
  }

  /** Number of events dropped due to buffer overflow. */
  get droppedEvents(): number {
    return this._droppedEvents
  }

  /**
   * Add an event to the buffer for batch sending.
   * Never throws. If the buffer is full, oldest events are dropped.
   */
  sendEvent(event: BaseEvent): void {
    try {
      const data: Record<string, unknown> = { ...event }

      if (this.redactInputs) delete data.tool_input
      if (this.redactOutputs) delete data.tool_output

      if (this._buffer.length >= MAX_BUFFER_SIZE) {
        const dropCount = this._buffer.length - MAX_BUFFER_SIZE + 1
        this._buffer.splice(0, dropCount)
        this._droppedEvents += dropCount
        console.warn(`bulwark: buffer full (${MAX_BUFFER_SIZE} events), dropped ${dropCount} oldest`)
      }

      this._buffer.push(data)
    } catch (e) {
      console.warn('bulwark: failed to buffer event', e)
    }
  }

  /**
   * Send all buffered events to the API.
   * Returns true if flush succeeded.
   */
  async flush(): Promise<boolean> {
    if (this._buffer.length === 0) return true

    const batch = [...this._buffer]
    this._buffer = []

    const success = await this._sendWithRetry('/v1/events/batch', { events: batch })

    if (success) {
      if (!this._healthy) {
        console.info(`bulwark: connection restored, flushed ${batch.length} buffered events`)
        this._healthy = true
      }
    } else {
      // Put events back (respecting max size)
      const combined = [...batch, ...this._buffer]
      if (combined.length > MAX_BUFFER_SIZE) {
        const overflow = combined.length - MAX_BUFFER_SIZE
        combined.splice(0, overflow)
        this._droppedEvents += overflow
      }
      this._buffer = combined

      if (this._healthy) {
        console.warn(
          `bulwark: API unreachable, entering degraded mode. ` +
          `Events will buffer in memory (max ${MAX_BUFFER_SIZE}).`
        )
        this._healthy = false
      }
    }

    return success
  }

  /**
   * Check if a session has been killed.
   * Fail-open: returns false if API is unreachable.
   */
  async checkKill(sessionId: string): Promise<boolean> {
    try {
      const resp = await this._fetch(`/v1/sessions/${sessionId}/status`, { method: 'GET' })
      if (resp.ok) {
        const data = (await resp.json()) as { killed?: boolean }
        return data.killed === true
      }
    } catch {
      // Fail-open
    }
    return false
  }

  /** Kill a session via the API. */
  async killSession(sessionId: string): Promise<boolean> {
    try {
      const resp = await this._fetch(`/v1/sessions/${sessionId}/kill`, { method: 'POST' })
      return resp.ok
    } catch {
      return false
    }
  }

  /** Stop background threads and flush remaining events. */
  async shutdown(): Promise<void> {
    this._running = false
    if (this._flushTimer) {
      clearInterval(this._flushTimer)
      this._flushTimer = null
    }
    try {
      await this.flush()
    } catch {
      // Best effort
    }
  }

  private async _sendWithRetry(path: string, payload: unknown): Promise<boolean> {
    for (let attempt = 0; attempt < MAX_RETRY_ATTEMPTS; attempt++) {
      try {
        const resp = await this._fetch(path, {
          method: 'POST',
          body: JSON.stringify(payload),
        })

        if (resp.status < 400) return true
        if (resp.status === 401) {
          console.error('bulwark: API returned 401 — check your API key.')
          return false
        }
        if (resp.status < 500) {
          console.warn(`bulwark: API returned ${resp.status}, not retrying`)
          return false
        }
        // 5xx — retry
      } catch {
        // Network error — retry
      }

      if (attempt < MAX_RETRY_ATTEMPTS - 1) {
        const backoff = RETRY_BACKOFF_BASE * (2 ** attempt)
        await new Promise(r => setTimeout(r, backoff))
      }
    }
    return false
  }

  private async _fetch(path: string, init: RequestInit): Promise<Response> {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), READ_TIMEOUT)

    try {
      return await fetch(`${this.endpoint}${path}`, {
        ...init,
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      })
    } finally {
      clearTimeout(timeout)
    }
  }
}
