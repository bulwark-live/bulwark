# @bulwark-ai/sdk

Real-time monitoring, alerting, and emergency kill switch for AI agents. TypeScript SDK.

## Install

```bash
npm install @bulwark-ai/sdk
```

## Quick Start

```typescript
import { init, session } from '@bulwark-ai/sdk';

init({
  apiKey: 'bwk_your_api_key',
  baseUrl: 'https://api.bulwark.live',
  agentName: 'my-agent',
});

const sess = session();
await sess.start();

await sess.trackToolCall({
  toolName: 'web_search',
  input: { query: 'latest news' },
  output: { results: ['...'] },
  durationMs: 150,
});

// Check if the session has been killed
if (sess.isKilled) {
  process.exit(1);
}

await sess.end();
```

## Features

- **Zero runtime dependencies** — uses native `fetch` (Node 18+)
- **Automatic retries** with exponential backoff on 5xx errors
- **Degraded mode** — buffers events when API is unreachable, flushes when reconnected
- **Fail-open kill switch** — if the API is down, agents keep running
- **CJS + ESM + TypeScript declarations** out of the box

## API

### `init(config)`
Initialize the SDK with your API key and base URL.

### `session(options?)`
Create a new monitoring session. Returns a `Session` object.

### `session.trackToolCall(options)`
Record a tool call event.

### `session.trackLlmCall(options)`
Record an LLM call event.

### `session.trackAction(options)`
Record a custom action event.

### `session.isKilled`
Check if the session has been killed via the dashboard.

## Links

- [Documentation](https://docs.bulwark.live)
- [GitHub](https://github.com/bulwark-live/bulwark)
- [Python SDK](https://pypi.org/project/bulwark-ai/)
