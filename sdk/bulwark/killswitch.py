"""Kill switch decorator for agent loops.

Provides a decorator that monitors the kill switch in a background thread
and raises ``KillSwitchTriggered`` (a ``SystemExit`` subclass) when a kill
signal is received, ensuring clean agent shutdown.
"""

from __future__ import annotations

import functools
import sys
import time
import threading
from typing import Callable

import bulwark


class KillSwitchTriggered(SystemExit):
    """Raised when a Bulwark kill switch is triggered.

    Inherits from ``SystemExit`` so it bypasses most exception handlers
    and cleanly terminates the process. Catch it explicitly if you need
    custom shutdown logic.

    Attributes:
        session_id: The ID of the session that was killed.

    Example::

        try:
            agent_loop(session)
        except bulwark.KillSwitchTriggered as e:
            print(f"Agent killed: session {e.session_id}")
            cleanup()
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Bulwark kill switch triggered for session {session_id}")


def killswitch(check_interval: int = 5) -> Callable:
    """Decorator that monitors the kill switch and exits if triggered.

    Wraps an agent function with a background kill switch monitor. The
    decorated function must accept a ``Session`` as one of its arguments.
    When a kill signal is detected, ``KillSwitchTriggered`` is raised.

    Args:
        check_interval: Seconds between kill switch checks (default 5).

    Returns:
        Decorator function.

    Raises:
        ValueError: If no ``Session`` argument is found in the call.

    Example::

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
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Find session in args
            session = None
            for arg in args:
                if hasattr(arg, "session_id") and hasattr(arg, "is_killed"):
                    session = arg
                    break
            for v in kwargs.values():
                if hasattr(v, "session_id") and hasattr(v, "is_killed"):
                    session = v
                    break

            if session is None:
                raise ValueError(
                    "@bulwark.killswitch requires a Session argument"
                )

            # Background kill check
            killed = threading.Event()

            def monitor():
                while not killed.is_set():
                    if session.is_killed():
                        killed.set()
                        return
                    time.sleep(check_interval)

            t = threading.Thread(target=monitor, daemon=True)
            t.start()

            try:
                return func(*args, **kwargs)
            finally:
                killed.set()

        return wrapper
    return decorator
