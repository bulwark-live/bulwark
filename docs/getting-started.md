# Getting Started with Bulwark

Add real-time monitoring and a kill switch to your AI agent in under 5 minutes.

## 1. Install the SDK

**Python:**
```bash
pip install bulwark-ai
```

**TypeScript:**
```bash
npm install @bulwark-ai/sdk
```

## 2. Get your API key

Sign up at [bulwark.live](https://bulwark.live) to request early access. You'll receive an API key that starts with `bwk_`.

## 3. Add monitoring to your agent

**Python — 4 lines to full observability:**

```python
import bulwark

bulwark.init(api_key="bwk_your_key", agent_name="my-agent")

with bulwark.session("customer-support-task") as s:
    # Track every tool call
    s.track_tool_call("search_kb", input={"query": "refund policy"}, duration_ms=120)

    # Track LLM usage and cost
    s.track_llm_call("claude-sonnet-4-6", input_tokens=800, cost_usd=0.003)

    # Track actions your agent takes
    s.track_action("send_reply", target="customer@example.com")

    # Check if someone hit the kill switch
    if s.is_killed():
        print("Agent stopped remotely.")
        break
```

**TypeScript:**

```typescript
import { init, session } from '@bulwark-ai/sdk';

init({ apiKey: 'bwk_your_key', baseUrl: 'https://api.bulwark.live', agentName: 'my-agent' });

const sess = session();
await sess.start();

await sess.trackToolCall({ toolName: 'search_kb', input: { query: 'refund policy' }, durationMs: 120 });
await sess.trackLlmCall({ model: 'claude-sonnet-4-6', inputTokens: 800, costUsd: 0.003 });

if (sess.isKilled) {
    process.exit(1);
}

await sess.end();
```

## 4. Open the dashboard

Go to [app.bulwark.live](https://app.bulwark.live), enter your API key, and you'll see:

- **Live event feed** — every tool call, LLM call, and action as it happens
- **Session timeline** — forensic view of exactly what an agent did and when
- **Kill button** — stop any agent session instantly
- **Alert rules** — set thresholds that auto-kill agents when breached

## 5. Set up alert rules

Create rules that automatically respond when agents misbehave. Example: kill any agent that makes more than 100 tool calls in 5 minutes.

```bash
curl -X POST https://api.bulwark.live/v1/rules \
  -H "Authorization: Bearer bwk_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Runaway Agent",
    "condition": {
      "metric": "tool_call_count",
      "operator": ">",
      "threshold": 100,
      "window_seconds": 300
    },
    "actions": [
      {"type": "dashboard_notification"},
      {"type": "auto_kill"}
    ]
  }'
```

### Available metrics

| Metric | What it watches |
|--------|----------------|
| `tool_call_count` | Total tool calls in time window |
| `tool_call_name` | Count of a specific tool |
| `llm_cost_usd` | Total LLM spend |
| `llm_token_count` | Total tokens consumed |
| `error_count` | Failed operations |
| `session_duration` | How long the session has been running |

### Available actions

| Action | What it does |
|--------|-------------|
| `dashboard_notification` | Alert in the dashboard |
| `webhook` | POST to your URL (3x retry) |
| `auto_kill` | Terminate the agent session immediately |

## 6. LangChain integration (optional)

If you use LangChain, get auto-instrumentation with zero code changes:

```bash
pip install bulwark-ai[langchain]
```

```python
from bulwark.integrations.langchain import BulwarkCallbackHandler

with bulwark.session("langchain-task") as s:
    handler = BulwarkCallbackHandler(session=s)
    agent.invoke({"input": "Analyze Q4 data"}, config={"callbacks": [handler]})
```

Every LLM call, tool invocation, and chain step is automatically tracked.

## How the kill switch works

1. Your agent's SDK polls `GET /v1/sessions/:id/status` every few seconds
2. When someone clicks "Kill" in the dashboard (or an auto-kill rule fires), the status changes
3. `s.is_killed()` returns `True` on the next poll
4. Your agent exits cleanly

The kill switch is **fail-open**: if the Bulwark API is unreachable, your agent keeps running. Safety monitoring should never be the thing that breaks your agent.

## Error handling

The SDK never crashes your agent:

- Events buffer in memory (up to 1,000) when the API is unreachable
- Automatic retry with exponential backoff
- All tracking methods become no-ops in degraded mode

```python
client = bulwark.get_client()
print(f"API reachable: {client.is_healthy}")
print(f"Buffered events: {client.buffer_size}")
```

## Next steps

- [Python SDK reference](https://pypi.org/project/bulwark-ai/)
- [TypeScript SDK reference](https://www.npmjs.com/package/@bulwark-ai/sdk)
- [API documentation](https://api.bulwark.live/docs)
- [GitHub](https://github.com/bulwark-live/bulwark)
