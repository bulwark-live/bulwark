"""Bulwark — The wall between AI agents and catastrophe.

Real-time monitoring, alerting, and emergency kill switch for AI agents.

Quick start::

    import bulwark

    bulwark.init(api_key="bwk_...", agent_name="my-agent")

    with bulwark.session("task-name") as s:
        s.track_tool_call("search_web", input={"q": "hello"})
        s.track_llm_call("gpt-4", input_tokens=100, output_tokens=50, cost_usd=0.01)

        if s.is_killed():
            break  # Remote kill switch triggered
"""

from __future__ import annotations

from typing import Optional

from bulwark.client import BulwarkClient
from bulwark.session import Session
from bulwark.killswitch import killswitch, KillSwitchTriggered

__version__ = "0.1.0"
__all__ = ["init", "session", "get_client", "killswitch", "KillSwitchTriggered"]

_client: Optional[BulwarkClient] = None


def init(
    api_key: str,
    agent_name: str,
    environment: str = "production",
    redact_inputs: bool = False,
    redact_outputs: bool = False,
    sample_rate: float = 1.0,
    endpoint: str = "https://api.bulwark.ai",
    flush_interval_ms: int = 1000,
    kill_check_interval_s: int = 10,
) -> None:
    """Initialize the Bulwark SDK.

    Must be called before creating sessions or tracking events.
    Creates a global client that manages API connection, event batching,
    and background flush threads.

    Args:
        api_key: Your Bulwark API key (starts with ``bwk_``).
        agent_name: Name identifying this agent (e.g. ``"research-agent"``).
        environment: Deployment environment (``"production"``, ``"staging"``, etc.).
        redact_inputs: If True, strip tool inputs before sending to API.
        redact_outputs: If True, strip tool outputs before sending to API.
        sample_rate: Fraction of events to send (0.0–1.0). Default 1.0 (all).
        endpoint: Bulwark API URL. Default ``https://api.bulwark.ai``.
        flush_interval_ms: How often to flush buffered events (milliseconds).
        kill_check_interval_s: How often sessions poll the kill switch (seconds).

    Example::

        import bulwark

        bulwark.init(
            api_key="bwk_abc123",
            agent_name="research-agent",
            endpoint="http://localhost:8000",
        )
    """
    global _client
    _client = BulwarkClient(
        api_key=api_key,
        agent_name=agent_name,
        environment=environment,
        redact_inputs=redact_inputs,
        redact_outputs=redact_outputs,
        sample_rate=sample_rate,
        endpoint=endpoint,
        flush_interval_ms=flush_interval_ms,
        kill_check_interval_s=kill_check_interval_s,
    )


def session(name: Optional[str] = None) -> Session:
    """Create a new monitored session.

    Returns a context manager that tracks the session lifecycle.
    Events are automatically batched and sent to the Bulwark API.
    Kill switch polling starts when the session is entered.

    Args:
        name: Optional human-readable session name.

    Returns:
        A ``Session`` context manager.

    Raises:
        RuntimeError: If ``bulwark.init()`` has not been called.

    Example::

        with bulwark.session("data-analysis") as s:
            s.track_tool_call("query_db", input={"sql": "SELECT ..."})

            if s.is_killed():
                print("Kill switch triggered!")
                break
    """
    if _client is None:
        raise RuntimeError("Bulwark not initialized. Call bulwark.init() first.")
    return Session(client=_client, name=name)


def get_client() -> BulwarkClient:
    """Get the global Bulwark client instance.

    Useful for checking connection health or accessing low-level client methods.

    Returns:
        The global ``BulwarkClient`` instance.

    Raises:
        RuntimeError: If ``bulwark.init()`` has not been called.

    Example::

        client = bulwark.get_client()
        print(f"Healthy: {client.is_healthy}")
        print(f"Buffered events: {client.buffer_size}")
    """
    if _client is None:
        raise RuntimeError("Bulwark not initialized. Call bulwark.init() first.")
    return _client
