# Bulwark — AI Safety Monitor & Kill Switch

Real-time monitoring, alerting, and emergency kill switch for AI agents.

```python
import bulwark

bulwark.init(api_key="bwk_...", agent_name="my-agent")

with bulwark.session("task-name") as s:
    s.track_tool_call("search_web", input={"q": "hello"})
    s.track_llm_call("gpt-4", input_tokens=100, cost_usd=0.01)

    if s.is_killed():
        break  # Remote kill switch triggered
```

## Features

- **Event tracking** — tool calls, LLM calls, actions with full payload capture
- **Kill switch** — remotely terminate any agent session in real-time
- **Alert rules** — auto-kill agents that breach thresholds (cost, tool calls, duration)
- **LangChain integration** — auto-instrument with zero code changes
- **Never crashes your agent** — degraded mode, retries, fail-open kill switch

## Install

```bash
pip install bulwark-ai
```

With LangChain support:

```bash
pip install bulwark-ai[langchain]
```

## Quick Start

```python
import bulwark

# Initialize
bulwark.init(
    api_key="bwk_...",
    agent_name="research-agent",
    endpoint="http://localhost:8000",
)

# Track a session
with bulwark.session("data-analysis") as s:
    s.track_tool_call("query_db", input={"sql": "SELECT ..."})
    s.track_llm_call("claude-sonnet-4-6", input_tokens=1200, cost_usd=0.005)
    s.track_action("send_email", target="user@example.com")

    if s.is_killed():
        print("Agent killed remotely!")
        break
```

## Kill Switch Decorator

```python
@bulwark.killswitch(check_interval=3)
def agent_loop(session):
    while True:
        session.track_tool_call("work")
        time.sleep(1)

with bulwark.session("my-task") as s:
    agent_loop(s)  # Exits cleanly on kill signal
```

## LangChain Auto-Instrumentation

```python
from bulwark.integrations.langchain import BulwarkCallbackHandler

with bulwark.session("langchain-task") as s:
    handler = BulwarkCallbackHandler(session=s)
    agent.invoke(input, config={"callbacks": [handler]})
```

## Error Handling

The SDK never crashes your agent:

- Events buffer in memory (up to 1,000) when the API is unreachable
- Automatic retry with exponential backoff on server errors
- Kill switch is fail-open (agent keeps running if API is down)

```python
client = bulwark.get_client()
print(f"Healthy: {client.is_healthy}")
print(f"Buffered: {client.buffer_size}")
```

## Links

- [Documentation](https://docs.bulwark.live)
- [Dashboard](https://app.bulwark.live)
- [GitHub](https://github.com/samrat-shamim/bulwark)
