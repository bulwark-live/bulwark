"""Session context manager for Bulwark monitoring."""

from __future__ import annotations

import logging
import platform
import sys
import time
import threading
import uuid
from typing import Any

import bulwark

logger = logging.getLogger("bulwark")
from bulwark.client import BulwarkClient
from bulwark.events import (
    ToolCallEvent,
    LLMCallEvent,
    ActionEvent,
    SessionStartEvent,
    SessionEndEvent,
)


class Session:
    """A monitored agent session.

    Tracks tool calls, LLM calls, and actions within a session context.
    Automatically sends session start/end events and polls the kill switch
    in a background thread.

    Use as a context manager::

        with bulwark.session("my-task") as s:
            s.track_tool_call("search", input={"q": "hello"})
            if s.is_killed():
                break

    All tracking methods are safe to call — they never raise exceptions.
    If the API is unreachable, events buffer in memory.
    """

    def __init__(self, client: BulwarkClient, name: str | None = None) -> None:
        self.client = client
        self.session_id = f"ses_{uuid.uuid4().hex[:12]}"
        self.name = name
        self._start_time = time.monotonic()
        self._event_count = 0
        self._killed = False
        self._kill_thread: threading.Thread | None = None

    def __enter__(self) -> Session:
        # Send session start event
        try:
            self.client.send_event(SessionStartEvent(
                session_id=self.session_id,
                agent_name=self.client.agent_name,
                environment=self.client.environment,
                sdk_version=bulwark.__version__,
                python_version=platform.python_version(),
            ))
        except Exception as e:
            logger.warning("bulwark: failed to send session start: %s", e)

        # Start kill switch polling
        self._start_kill_polling()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            elapsed = int((time.monotonic() - self._start_time) * 1000)
            self.client.send_event(SessionEndEvent(
                session_id=self.session_id,
                agent_name=self.client.agent_name,
                environment=self.client.environment,
                total_events=self._event_count,
                total_duration_ms=elapsed,
                status="killed" if self._killed else ("error" if exc_type else "success"),
            ))
            self.client.flush()
        except Exception as e:
            logger.warning("bulwark: failed to send session end: %s", e)
        return None

    def track_tool_call(
        self,
        tool: str,
        input: Any = None,
        output: Any = None,
        duration_ms: int | None = None,
        status: str = "success",
    ) -> None:
        """Track an agent tool call.

        Never raises — failures are logged and the event is dropped.

        Args:
            tool: Name of the tool (e.g. ``"search_web"``, ``"execute_code"``).
            input: Tool input data (any JSON-serializable value).
            output: Tool output data (any JSON-serializable value).
            duration_ms: How long the tool call took in milliseconds.
            status: ``"success"`` or ``"error"``.

        Example::

            s.track_tool_call(
                "search_web",
                input={"query": "latest news"},
                output={"results": 10},
                duration_ms=350,
            )
        """
        try:
            self._event_count += 1
            self.client.send_event(ToolCallEvent(
                session_id=self.session_id,
                agent_name=self.client.agent_name,
                environment=self.client.environment,
                tool_name=tool,
                tool_input=input,
                tool_output=output,
                duration_ms=duration_ms,
                status=status,
            ))
        except Exception as e:
            logger.warning("bulwark: failed to track tool call: %s", e)

    def track_llm_call(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        provider: str = "",
        prompt_summary: str = "",
        duration_ms: int | None = None,
    ) -> None:
        """Track an LLM API call.

        Never raises — failures are logged and the event is dropped.

        Args:
            model: Model identifier (e.g. ``"gpt-4"``, ``"claude-sonnet-4-6"``).
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.
            cost_usd: Cost of this call in USD.
            provider: LLM provider (e.g. ``"openai"``, ``"anthropic"``).
            prompt_summary: Brief description of the prompt purpose.
            duration_ms: How long the LLM call took in milliseconds.

        Example::

            s.track_llm_call(
                "claude-sonnet-4-6",
                input_tokens=1200,
                output_tokens=400,
                cost_usd=0.005,
                provider="anthropic",
                prompt_summary="Planning next research step",
            )
        """
        try:
            self._event_count += 1
            self.client.send_event(LLMCallEvent(
                session_id=self.session_id,
                agent_name=self.client.agent_name,
                environment=self.client.environment,
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                prompt_summary=prompt_summary,
                duration_ms=duration_ms,
            ))
        except Exception as e:
            logger.warning("bulwark: failed to track LLM call: %s", e)

    def track_action(
        self,
        action: str,
        target: str = "",
        metadata: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        status: str = "success",
    ) -> None:
        """Track a generic agent action.

        Use for any agent behavior that isn't a tool call or LLM call.
        Never raises — failures are logged and the event is dropped.

        Args:
            action: Action name (e.g. ``"deploy"``, ``"approve"``, ``"send_email"``).
            target: What the action targets (e.g. a URL, file path, user ID).
            metadata: Arbitrary key-value metadata.
            duration_ms: How long the action took in milliseconds.
            status: ``"success"`` or ``"error"``.

        Example::

            s.track_action(
                "send_email",
                target="user@example.com",
                metadata={"subject": "Weekly Report"},
            )
        """
        try:
            self._event_count += 1
            self.client.send_event(ActionEvent(
                session_id=self.session_id,
                agent_name=self.client.agent_name,
                environment=self.client.environment,
                action=action,
                target=target,
                metadata=metadata or {},
                duration_ms=duration_ms,
                status=status,
            ))
        except Exception as e:
            logger.warning("bulwark: failed to track action: %s", e)

    def is_killed(self) -> bool:
        """Check if this session has been killed via the remote kill switch.

        Returns:
            True if a kill signal has been received.

        Example::

            while True:
                if s.is_killed():
                    print("Agent killed remotely!")
                    break
                do_work()
        """
        return self._killed

    def _start_kill_polling(self) -> None:
        """Start background thread to poll kill switch."""
        def poll():
            while not self._killed:
                try:
                    self._killed = self.client.check_kill(self.session_id)
                    if self._killed:
                        break
                except Exception as e:
                    logger.debug("bulwark: kill poll error (fail-open): %s", e)
                time.sleep(self.client.kill_check_interval_s)

        self._kill_thread = threading.Thread(target=poll, daemon=True)
        self._kill_thread.start()
