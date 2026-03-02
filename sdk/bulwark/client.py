"""HTTP client for Bulwark API.

Designed to never crash the host agent. All failures are handled gracefully
with logging, retries, and degraded mode fallbacks.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import httpx

from bulwark.events import BaseEvent

logger = logging.getLogger("bulwark")

# Limits
MAX_BUFFER_SIZE = 1000
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 1.0  # seconds — 1s, 2s, 4s
RECONNECT_INTERVAL = 30.0  # seconds between reconnection attempts
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 10.0


class BulwarkClient:
    """Manages connection to Bulwark API and batches event telemetry.

    The client operates in two modes:
    - **Healthy**: events are batched and flushed to the API normally.
    - **Degraded**: API is unreachable. Events buffer in memory (up to 1000).
      A background thread retries connection every 30s. When the API comes
      back, buffered events are flushed automatically.

    The client will never raise exceptions to the caller. All failures are
    logged and handled internally.
    """

    def __init__(
        self,
        api_key: str,
        agent_name: str,
        environment: str = "production",
        redact_inputs: bool = False,
        redact_outputs: bool = False,
        sample_rate: float = 1.0,
        endpoint: str = "https://api.bulwark.live",
        flush_interval_ms: int = 1000,
        kill_check_interval_s: int = 10,
    ) -> None:
        self.api_key = api_key
        self.agent_name = agent_name
        self.environment = environment
        self.redact_inputs = redact_inputs
        self.redact_outputs = redact_outputs
        self.sample_rate = sample_rate
        self.endpoint = endpoint.rstrip("/")
        self.flush_interval_s = flush_interval_ms / 1000
        self.kill_check_interval_s = kill_check_interval_s

        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._healthy = True
        self._dropped_events = 0

        self._http = httpx.Client(
            base_url=self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(CONNECT_TIMEOUT, read=READ_TIMEOUT),
        )

        # Start background flush thread
        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    @property
    def is_healthy(self) -> bool:
        """True when the API connection is working normally."""
        return self._healthy

    @property
    def buffer_size(self) -> int:
        """Number of events currently buffered."""
        with self._lock:
            return len(self._buffer)

    @property
    def dropped_events(self) -> int:
        """Number of events dropped due to buffer overflow."""
        return self._dropped_events

    def send_event(self, event: BaseEvent) -> None:
        """Add an event to the buffer for batch sending.

        Never raises. If the buffer is full, the oldest events are dropped.
        """
        try:
            data = event.to_dict()
        except Exception:
            logger.warning("bulwark: failed to serialize event, dropping")
            return

        # Apply redaction
        if self.redact_inputs and "tool_input" in data:
            data.pop("tool_input", None)
        if self.redact_outputs and "tool_output" in data:
            data.pop("tool_output", None)

        with self._lock:
            if len(self._buffer) >= MAX_BUFFER_SIZE:
                # Drop oldest events to make room
                drop_count = len(self._buffer) - MAX_BUFFER_SIZE + 1
                self._buffer = self._buffer[drop_count:]
                self._dropped_events += drop_count
                logger.warning(
                    "bulwark: buffer full (%d events), dropped %d oldest",
                    MAX_BUFFER_SIZE, drop_count,
                )
            self._buffer.append(data)

    def flush(self) -> bool:
        """Send all buffered events to the API.

        Returns True if flush succeeded, False otherwise. Never raises.
        """
        with self._lock:
            if not self._buffer:
                return True
            batch = self._buffer.copy()
            self._buffer.clear()

        success = self._send_with_retry("/v1/events/batch", {"events": batch})

        if success:
            if not self._healthy:
                logger.info("bulwark: connection restored, flushed %d buffered events", len(batch))
                self._healthy = True
        else:
            # Put events back in buffer (respecting max size)
            with self._lock:
                combined = batch + self._buffer
                if len(combined) > MAX_BUFFER_SIZE:
                    overflow = len(combined) - MAX_BUFFER_SIZE
                    combined = combined[overflow:]
                    self._dropped_events += overflow
                self._buffer = combined

            if self._healthy:
                logger.warning(
                    "bulwark: API unreachable, entering degraded mode. "
                    "Events will buffer in memory (max %d). "
                    "Will retry every %ds.",
                    MAX_BUFFER_SIZE, int(RECONNECT_INTERVAL),
                )
                self._healthy = False

        return success

    def check_kill(self, session_id: str) -> bool:
        """Check if a session has been killed.

        Fail-open: if the API is unreachable, returns False (agent keeps running).
        Never raises.
        """
        try:
            resp = self._http.get(f"/v1/sessions/{session_id}/status")
            if resp.status_code == 200:
                return resp.json().get("killed", False)
            if resp.status_code == 401:
                logger.warning("bulwark: kill check returned 401 — invalid API key")
        except (httpx.HTTPError, Exception) as e:
            logger.debug("bulwark: kill check failed (fail-open): %s", e)
        return False

    def kill_session(self, session_id: str) -> bool:
        """Kill a session via the API. Never raises."""
        try:
            resp = self._http.post(f"/v1/sessions/{session_id}/kill")
            return resp.status_code == 200
        except (httpx.HTTPError, Exception) as e:
            logger.warning("bulwark: kill_session failed: %s", e)
            return False

    def _send_with_retry(self, path: str, payload: dict) -> bool:
        """POST with exponential backoff retry on 5xx / network errors."""
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                resp = self._http.post(path, json=payload)
                if resp.status_code < 400:
                    return True
                if resp.status_code == 401:
                    logger.error(
                        "bulwark: API returned 401 — check your API key. "
                        "Entering degraded mode."
                    )
                    return False
                if resp.status_code < 500:
                    # 4xx (non-401) — don't retry, it won't help
                    logger.warning("bulwark: API returned %d, not retrying", resp.status_code)
                    return False
                # 5xx — retry
                logger.debug("bulwark: API returned %d, retrying (%d/%d)",
                             resp.status_code, attempt + 1, MAX_RETRY_ATTEMPTS)
            except (httpx.HTTPError, Exception) as e:
                logger.debug("bulwark: request failed: %s, retrying (%d/%d)",
                             e, attempt + 1, MAX_RETRY_ATTEMPTS)

            if attempt < MAX_RETRY_ATTEMPTS - 1:
                backoff = RETRY_BACKOFF_BASE * (2 ** attempt)
                time.sleep(backoff)

        return False

    def _flush_loop(self) -> None:
        """Background loop to periodically flush events."""
        while self._running:
            time.sleep(self.flush_interval_s)
            try:
                self.flush()
            except Exception as e:
                # Should never happen since flush() catches everything,
                # but defense in depth
                logger.debug("bulwark: unexpected error in flush loop: %s", e)

    def shutdown(self) -> None:
        """Stop background threads and flush remaining events. Never raises."""
        self._running = False
        try:
            self.flush()
        except Exception:
            pass
        try:
            self._http.close()
        except Exception:
            pass
