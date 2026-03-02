"""Event types and serialization for Bulwark telemetry."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


def _hash_payload(data: Any) -> str:
    return f"sha256:{hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]}"


@dataclass
class BaseEvent:
    event_type: str = ""
    session_id: str = ""
    agent_name: str = ""
    environment: str = ""
    event_id: str = field(default_factory=_new_id)
    timestamp: str = field(default_factory=_now)
    duration_ms: int | None = None
    status: str = "success"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class ToolCallEvent(BaseEvent):
    event_type: str = "tool_call"
    tool_name: str = ""
    tool_input: Any = None
    tool_output: Any = None
    tool_input_hash: str = ""
    tool_output_hash: str = ""

    def __post_init__(self):
        if self.tool_input is not None and not self.tool_input_hash:
            self.tool_input_hash = _hash_payload(self.tool_input)
        if self.tool_output is not None and not self.tool_output_hash:
            self.tool_output_hash = _hash_payload(self.tool_output)


@dataclass
class LLMCallEvent(BaseEvent):
    event_type: str = "llm_call"
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    prompt_summary: str = ""


@dataclass
class ActionEvent(BaseEvent):
    event_type: str = "action"
    action: str = ""
    target: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionStartEvent(BaseEvent):
    event_type: str = "session_start"
    sdk_version: str = ""
    python_version: str = ""
    framework: str = ""
    framework_version: str = ""


@dataclass
class SessionEndEvent(BaseEvent):
    event_type: str = "session_end"
    total_events: int = 0
    total_duration_ms: int = 0
