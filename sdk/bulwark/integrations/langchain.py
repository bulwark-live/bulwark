"""LangChain auto-instrumentation for Bulwark.

Automatically tracks all tool calls and LLM calls made through LangChain
agents and chains. No manual ``track_*`` calls needed.

Requires ``langchain-core``. Install with::

    pip install bulwark-ai[langchain]

Example::

    import bulwark
    from bulwark.integrations.langchain import BulwarkCallbackHandler

    bulwark.init(api_key="bwk_...", agent_name="my-langchain-agent")

    with bulwark.session("research-task") as s:
        handler = BulwarkCallbackHandler(session=s)
        agent = create_react_agent(llm, tools)
        agent.invoke(
            {"input": "Find the latest AI papers"},
            config={"callbacks": [handler]},
        )
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    raise ImportError(
        "LangChain integration requires langchain-core. "
        "Install with: pip install bulwark-ai[langchain]"
    )

from bulwark.session import Session


class BulwarkCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that auto-instruments agent telemetry.

    Hooks into LangChain's callback system to automatically track:
    - Tool calls (start, end, error) with duration and status
    - LLM calls (start, end) with token counts and model info

    Args:
        session: An active Bulwark ``Session`` to send events to.

    Example::

        with bulwark.session("task") as s:
            handler = BulwarkCallbackHandler(session=s)
            chain.invoke(input, config={"callbacks": [handler]})
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tool_starts: dict[str, float] = {}
        self._llm_starts: dict[str, float] = {}

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._tool_starts[str(run_id)] = time.monotonic()

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        start = self._tool_starts.pop(str(run_id), None)
        duration_ms = int((time.monotonic() - start) * 1000) if start else None
        tool_name = kwargs.get("name", "unknown")

        self.session.track_tool_call(
            tool=tool_name,
            input=kwargs.get("input", None),
            output=str(output)[:1000],
            duration_ms=duration_ms,
            status="success",
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        start = self._tool_starts.pop(str(run_id), None)
        duration_ms = int((time.monotonic() - start) * 1000) if start else None

        self.session.track_tool_call(
            tool=kwargs.get("name", "unknown"),
            output=str(error)[:500],
            duration_ms=duration_ms,
            status="failure",
        )

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._llm_starts[str(run_id)] = time.monotonic()

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        start = self._llm_starts.pop(str(run_id), None)
        duration_ms = int((time.monotonic() - start) * 1000) if start else None

        token_usage = {}
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})

        self.session.track_llm_call(
            model=kwargs.get("invocation_params", {}).get("model", "unknown"),
            input_tokens=token_usage.get("prompt_tokens", 0),
            output_tokens=token_usage.get("completion_tokens", 0),
            duration_ms=duration_ms,
        )
