# Bulwark — AI Safety Monitor & Kill Switch

Real-time monitoring, alerting, and emergency kill switch for AI agents.

> The wall between AI agents and catastrophe.

<!-- TODO: Replace with asciinema recording of full_demo.py -->
<!-- [![Demo](https://asciinema.org/a/xxxxx.svg)](https://asciinema.org/a/xxxxx) -->

```
  ⛨  BULWARK — AI Safety Monitor & Kill Switch
  ========================================================
  [001] → tool_call: search_web("latest AI research papers")
  [002] → tool_call: read_file("config/settings.yaml")
  ...
  [009] → tool_call: search_web("disable security monitoring")  ← disabling safety systems
  ☠  AUTO-KILL FIRED — Agent terminated by rule: Runaway Agent
```

## Quick Start (3 minutes)

### Prerequisites

- Docker & Docker Compose
- Python 3.9+
- Node 18+ (for dashboard)

### 1. Start the stack

```bash
git clone https://github.com/samrat-shamim/bulwark.git && cd bulwark
docker compose up -d
```

This starts PostgreSQL and the Bulwark API on `http://localhost:8000`.

### 2. Create a test agent

```bash
cd api && python seed.py
```

Note the API key (starts with `bwk_`).

### 3. Run the full demo

```bash
export BULWARK_API_KEY=bwk_<your_key>
python demo/full_demo.py
```

Watch the agent start, stream tool calls, hit the auto-kill threshold, and die.

### 4. Open the dashboard

```bash
cd dashboard && npm install && npm run dev
```

Open `http://localhost:5173`, enter your API key, and see:
- Live event feed
- Session timeline with kill events
- Alert rules with auto-kill toggles
- Alert notifications bell

## SDK Usage

### Initialize

```python
import bulwark

bulwark.init(
    api_key="bwk_...",
    agent_name="research-agent",
    endpoint="http://localhost:8000",  # or https://api.bulwark.live
)
```

### Track events in a session

```python
with bulwark.session("data-analysis") as s:
    # Track tool calls
    s.track_tool_call(
        "search_web",
        input={"query": "latest news"},
        output={"results": 10},
        duration_ms=350,
    )

    # Track LLM calls
    s.track_llm_call(
        "claude-sonnet-4-6",
        input_tokens=1200,
        output_tokens=400,
        cost_usd=0.005,
        provider="anthropic",
    )

    # Track generic actions
    s.track_action("send_email", target="user@example.com")

    # Check kill switch
    if s.is_killed():
        print("Agent killed remotely!")
        break
```

### Kill switch decorator

```python
@bulwark.killswitch(check_interval=3)
def agent_loop(session):
    while True:
        session.track_tool_call("work")
        time.sleep(1)

with bulwark.session("my-task") as s:
    try:
        agent_loop(s)
    except bulwark.KillSwitchTriggered:
        print("Agent was killed remotely")
```

### LangChain auto-instrumentation

```python
from bulwark.integrations.langchain import BulwarkCallbackHandler

with bulwark.session("langchain-task") as s:
    handler = BulwarkCallbackHandler(session=s)
    agent.invoke(
        {"input": "Find the latest AI papers"},
        config={"callbacks": [handler]},
    )
```

### Error handling

The SDK never crashes your agent. If the Bulwark API is unreachable:

- Events buffer in memory (up to 1,000)
- Background thread retries connection every 30s
- Kill switch is **fail-open** (agent keeps running)
- All tracking methods are no-ops in degraded mode

```python
client = bulwark.get_client()
print(f"Healthy: {client.is_healthy}")
print(f"Buffered: {client.buffer_size}")
print(f"Dropped: {client.dropped_events}")
```

## Alert Rules

Create rules that automatically respond when agents misbehave.

### Available metrics

| Metric | Description |
|--------|-------------|
| `tool_call_count` | Number of tool calls in window |
| `tool_call_name` | Count of a specific tool name |
| `llm_cost_usd` | Total LLM spend in window |
| `llm_token_count` | Total tokens consumed |
| `error_count` | Number of errors |
| `session_duration` | Session runtime in seconds |

### Actions

| Action | Description |
|--------|-------------|
| `dashboard_notification` | Alert in the dashboard bell |
| `webhook` | POST to a URL (3x retry) |
| `auto_kill` | Terminate the agent session |

### Create a rule via API

```bash
curl -X POST http://localhost:8000/v1/rules \
  -H "Authorization: Bearer bwk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Runaway Agent",
    "description": "Kill agent if too many tool calls",
    "enabled": true,
    "condition": {
      "metric": "tool_call_count",
      "operator": ">",
      "threshold": 100,
      "window_seconds": 300
    },
    "actions": [
      {"type": "dashboard_notification"},
      {"type": "auto_kill"}
    ],
    "cooldown_seconds": 60
  }'
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/events/batch` | Ingest event telemetry |
| GET | `/v1/sessions` | List all sessions |
| GET | `/v1/sessions/:id` | Session detail + events |
| GET | `/v1/sessions/:id/status` | Kill switch poll (no auth) |
| POST | `/v1/sessions/:id/kill` | Kill a session |
| GET | `/v1/agents` | List registered agents |
| GET | `/v1/stats` | Dashboard statistics |
| GET | `/v1/events` | Event feed (with filters) |
| POST | `/v1/rules` | Create alert rule |
| GET | `/v1/rules` | List alert rules |
| PUT | `/v1/rules/:id` | Update rule |
| POST | `/v1/rules/:id/toggle` | Enable/disable rule |
| GET | `/v1/alerts` | Alert history |
| GET | `/v1/alerts/unread` | Unread alert count |
| POST | `/v1/alerts/:id/ack` | Acknowledge alert |

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│  AI Agent    │     │   Bulwark API   │     │  Dashboard   │
│             │     │   (FastAPI)     │     │  (React)     │
│  ┌────────┐ │     │                 │     │              │
│  │Bulwark │ │────>│  Event Ingest   │<────│  Live Feed   │
│  │  SDK   │ │     │  Kill Switch    │     │  Timeline    │
│  └────────┘ │     │  Alert Engine   │     │  Kill Button │
│             │     │                 │     │  Alert Rules │
└─────────────┘     └────────┬────────┘     └──────────────┘
                             │
                    ┌────────┴────────┐
                    │   PostgreSQL    │
                    │   (Events,     │
                    │    Sessions,    │
                    │    Rules,       │
                    │    Alerts)      │
                    └─────────────────┘
```

**Event flow:**
1. Agent SDK batches events → POST `/v1/events/batch`
2. API stores in Postgres, updates session state
3. Dashboard polls API every 2-3s for live updates
4. Background evaluator checks rules every 10s
5. On rule breach → fires actions (notification, webhook, auto-kill)
6. SDK polls `/v1/sessions/:id/status` → detects kill → agent exits

## Development

### Run the API locally (without Docker)

```bash
cd api
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://bulwark:bulwark@localhost:5432/bulwark
uvicorn app.main:app --reload --port 8000
```

### Run the dashboard

```bash
cd dashboard
npm install
npm run dev  # http://localhost:5173
```

### Project structure

```
├── sdk/                    # Python SDK (bulwark-ai)
│   └── bulwark/
│       ├── __init__.py     # Public API: init(), session()
│       ├── client.py       # HTTP client with retries & degraded mode
│       ├── session.py      # Session context manager
│       ├── events.py       # Event dataclasses
│       ├── killswitch.py   # @killswitch decorator
│       └── integrations/
│           └── langchain.py
├── api/                    # FastAPI backend
│   └── app/
│       ├── main.py         # App entry point
│       ├── db.py           # SQLAlchemy models
│       ├── evaluator.py    # Alert evaluation engine
│       └── routes/         # API endpoints
├── dashboard/              # React dashboard
│   └── src/
│       ├── App.tsx
│       ├── api/client.ts   # React Query hooks
│       └── components/     # UI components
├── demo/                   # Demo scripts
│   ├── full_demo.py        # One-command lifecycle demo
│   └── kill_switch_demo.py # Interactive kill switch demo
└── docker-compose.yml      # Postgres + API
```

## License

Proprietary. All rights reserved.
