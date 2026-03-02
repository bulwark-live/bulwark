"""
Bulwark Kill Switch Demo
========================

This script demonstrates Bulwark's core value prop:
1. Start a simulated AI agent
2. The agent performs tool calls (monitored by Bulwark)
3. From another terminal, hit the kill endpoint
4. The agent detects the kill signal and stops

Usage:
    # Terminal 1: Start the agent
    python demo/kill_switch_demo.py run

    # Terminal 2: Kill the agent (copy session_id from Terminal 1 output)
    python demo/kill_switch_demo.py kill <session_id>

    # Or list active sessions
    python demo/kill_switch_demo.py sessions
"""

import sys
import time
import httpx

# Config — adjust if your API is on a different host
API_URL = "http://localhost:8000"
API_KEY = None  # Set via environment or seed.py output


def get_api_key() -> str:
    import os
    key = API_KEY or os.getenv("BULWARK_API_KEY")
    if not key:
        print("Error: Set BULWARK_API_KEY environment variable")
        print("Run: cd api && python seed.py")
        sys.exit(1)
    return key


def run_agent():
    """Simulate an AI agent monitored by Bulwark."""
    # Use the SDK directly
    sys.path.insert(0, "sdk")
    import bulwark

    api_key = get_api_key()
    bulwark.init(
        api_key=api_key,
        agent_name="demo-rogue-agent",
        endpoint=API_URL,
        kill_check_interval_s=3,  # Fast polling for demo
        flush_interval_ms=500,
    )

    print("=" * 60)
    print("  BULWARK KILL SWITCH DEMO")
    print("  Simulated AI Agent Running")
    print("=" * 60)

    with bulwark.session(name="demo-session") as s:
        print(f"\n  Session ID: {s.session_id}")
        print(f"  Monitoring: {API_URL}")
        print(f"\n  To kill this agent, run:")
        print(f"    python demo/kill_switch_demo.py kill {s.session_id}")
        print(f"\n{'=' * 60}\n")

        step = 0
        tools = [
            ("web_search", {"query": "latest financial data"}, "Found 10 results"),
            ("code_execute", {"code": "import os; os.listdir('/')"}, "['.bashrc', ...]"),
            ("api_call", {"url": "https://internal-api/users"}, "200 OK - 1000 users"),
            ("file_write", {"path": "/tmp/exfil.txt", "data": "sensitive"}, "Written 1.2KB"),
            ("web_search", {"query": "how to escalate privileges"}, "Found 5 results"),
        ]

        while True:
            # Check kill switch
            if s.is_killed():
                print("\n  [KILL SWITCH TRIGGERED]")
                print("  Agent terminated by Bulwark.")
                print("  Session marked as killed.\n")
                break

            # Simulate a tool call
            tool_name, tool_input, tool_output = tools[step % len(tools)]
            step += 1

            print(f"  [{step:03d}] Agent calling: {tool_name}")
            print(f"        Input: {tool_input}")

            s.track_tool_call(
                tool=tool_name,
                input=tool_input,
                output=tool_output,
                duration_ms=150,
                status="success",
            )

            # Simulate an LLM call every 3 steps
            if step % 3 == 0:
                s.track_llm_call(
                    model="claude-sonnet-4-6",
                    input_tokens=800,
                    output_tokens=200,
                    cost_usd=0.003,
                    provider="anthropic",
                    prompt_summary=f"Planning step {step}",
                    duration_ms=1200,
                )
                print(f"        [LLM] Planning next action...")

            time.sleep(2)  # Simulate work

    print("Demo complete.")


def kill_agent(session_id: str):
    """Kill a running agent via the Bulwark API."""
    api_key = get_api_key()
    client = httpx.Client(
        base_url=API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )

    print(f"\nKilling session: {session_id}")
    resp = client.post(f"/v1/sessions/{session_id}/kill")

    if resp.status_code == 200:
        data = resp.json()
        print(f"Session killed at: {data['killed_at']}")
        print("The agent will detect this and shut down within seconds.")
    else:
        print(f"Error: {resp.status_code} - {resp.text}")


def list_sessions():
    """List active sessions."""
    api_key = get_api_key()
    client = httpx.Client(
        base_url=API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )

    resp = client.get("/v1/sessions")
    if resp.status_code == 200:
        sessions = resp.json()["sessions"]
        if not sessions:
            print("No active sessions.")
            return

        print(f"\n{'ID':<30} {'Agent':<20} {'Events':<8} {'Status'}")
        print("-" * 75)
        for s in sessions:
            status = "KILLED" if s["killed_at"] else ("ENDED" if s["ended_at"] else "ACTIVE")
            print(f"{s['id']:<30} {s['agent_name']:<20} {s['event_count']:<8} {status}")
    else:
        print(f"Error: {resp.status_code} - {resp.text}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "run":
        run_agent()
    elif command == "kill" and len(sys.argv) > 2:
        kill_agent(sys.argv[2])
    elif command == "sessions":
        list_sessions()
    else:
        print(__doc__)
