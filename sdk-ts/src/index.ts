/**
 * Bulwark — The wall between AI agents and catastrophe.
 *
 * Real-time monitoring, alerting, and emergency kill switch for AI agents.
 *
 * @example
 * ```ts
 * import * as bulwark from '@bulwark-ai/sdk'
 *
 * bulwark.init({ apiKey: 'bwk_...', agentName: 'my-agent' })
 *
 * const session = bulwark.session('task-name')
 * await session.start()
 *
 * session.trackToolCall({ tool: 'search', input: { q: 'hello' } })
 * session.trackLlmCall({ model: 'gpt-4', inputTokens: 100, costUsd: 0.01 })
 *
 * if (session.isKilled) {
 *   console.log('Kill switch triggered!')
 * }
 *
 * await session.end()
 * ```
 *
 * @packageDocumentation
 */

import { BulwarkClient } from './client'
import { Session } from './session'
import type { BulwarkConfig } from './types'

export type {
  BulwarkConfig,
  TrackToolCallOptions,
  TrackLlmCallOptions,
  TrackActionOptions,
} from './types'

export { BulwarkClient } from './client'
export { Session } from './session'

let _client: BulwarkClient | null = null

/**
 * Initialize the Bulwark SDK.
 *
 * Must be called before creating sessions or tracking events.
 *
 * @example
 * ```ts
 * import * as bulwark from '@bulwark-ai/sdk'
 *
 * bulwark.init({
 *   apiKey: 'bwk_abc123',
 *   agentName: 'research-agent',
 *   endpoint: 'http://localhost:8000',
 * })
 * ```
 */
export function init(config: BulwarkConfig): void {
  _client = new BulwarkClient({
    apiKey: config.apiKey,
    agentName: config.agentName,
    environment: config.environment ?? 'production',
    endpoint: config.endpoint ?? 'https://api.bulwark.ai',
    redactInputs: config.redactInputs ?? false,
    redactOutputs: config.redactOutputs ?? false,
    flushIntervalMs: config.flushIntervalMs ?? 1000,
    killCheckIntervalMs: config.killCheckIntervalMs ?? 10000,
  })
}

/**
 * Create a new monitored session.
 *
 * Call `.start()` to begin tracking, `.end()` to stop.
 *
 * @example
 * ```ts
 * const s = bulwark.session('data-analysis')
 * await s.start()
 * s.trackToolCall({ tool: 'query_db', input: { sql: 'SELECT ...' } })
 * await s.end()
 * ```
 */
export function session(name?: string): Session {
  if (!_client) {
    throw new Error('Bulwark not initialized. Call bulwark.init() first.')
  }
  return new Session(_client, name)
}

/**
 * Get the global Bulwark client instance.
 *
 * @example
 * ```ts
 * const client = bulwark.getClient()
 * console.log(`Healthy: ${client.isHealthy}`)
 * ```
 */
export function getClient(): BulwarkClient {
  if (!_client) {
    throw new Error('Bulwark not initialized. Call bulwark.init() first.')
  }
  return _client
}

/**
 * Shut down the SDK — flush remaining events and stop timers.
 * Call this before process exit.
 */
export async function shutdown(): Promise<void> {
  if (_client) {
    await _client.shutdown()
    _client = null
  }
}
