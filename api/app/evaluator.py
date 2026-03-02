"""Alert evaluation engine — runs as a background task."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy import select, func

from app.db import async_session, AlertRule, Alert, Event, SessionRecord

logger = logging.getLogger("bulwark.evaluator")

# Track cooldowns in memory (rule_id -> last_fire_time)
_cooldowns: dict[str, datetime] = {}


async def evaluate_rules():
    """Main evaluation loop. Runs every 10 seconds."""
    while True:
        try:
            await _evaluate_cycle()
        except Exception as e:
            logger.error(f"Evaluation cycle error: {e}")
        await asyncio.sleep(10)


async def _evaluate_cycle():
    """Single evaluation pass over all enabled rules."""
    async with async_session() as db:
        result = await db.execute(
            select(AlertRule).where(AlertRule.enabled == True)
        )
        rules = result.scalars().all()

    for rule in rules:
        try:
            breached, metric_value, session_id = await _evaluate_rule(rule)
            if breached and not _in_cooldown(rule):
                await _fire_alert(rule, metric_value, session_id)
                _cooldowns[rule.id] = datetime.now(timezone.utc)
        except Exception as e:
            logger.error(f"Rule {rule.id} evaluation error: {e}")


async def _evaluate_rule(rule: AlertRule) -> tuple[bool, float, str]:
    """Evaluate a single rule. Returns (breached, metric_value, session_id)."""
    condition = rule.condition
    metric = condition.get("metric", "")
    operator = condition.get("operator", "gt")
    threshold = float(condition.get("threshold", 0))
    window = int(condition.get("window_seconds", 300))

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window)

    async with async_session() as db:
        # Build base query scoped to this agent's sessions
        base_q = (
            select(Event)
            .join(SessionRecord, Event.session_id == SessionRecord.id)
            .where(SessionRecord.agent_id == rule.agent_id)
            .where(Event.timestamp >= cutoff)
        )

        # Apply scope filters
        scope = rule.scope or {}
        if scope.get("environment"):
            base_q = base_q.where(SessionRecord.environment == scope["environment"])

        # Only evaluate active sessions
        base_q = base_q.where(SessionRecord.killed_at.is_(None))
        base_q = base_q.where(SessionRecord.ended_at.is_(None))

        if metric == "tool_call_count":
            q = base_q.where(Event.event_type == "tool_call")
            result = await db.execute(q)
            events = result.scalars().all()
            value = float(len(events))
            # Find the session with most events
            session_id = _most_active_session(events)

        elif metric == "tool_call_name":
            tool_name = str(threshold)  # For name matching, threshold holds the name
            threshold = 1.0  # Any match = breach
            q = base_q.where(Event.event_type == "tool_call")
            result = await db.execute(q)
            events = result.scalars().all()
            matches = [e for e in events if (e.payload or {}).get("tool_name") == tool_name]
            value = float(len(matches))
            session_id = _most_active_session(matches) if matches else ""

        elif metric == "llm_cost_usd":
            q = base_q.where(Event.event_type == "llm_call")
            result = await db.execute(q)
            events = result.scalars().all()
            value = sum((e.payload or {}).get("cost_usd", 0) for e in events)
            session_id = _most_active_session(events)

        elif metric == "llm_token_count":
            q = base_q.where(Event.event_type == "llm_call")
            result = await db.execute(q)
            events = result.scalars().all()
            value = sum(
                (e.payload or {}).get("input_tokens", 0) + (e.payload or {}).get("output_tokens", 0)
                for e in events
            )
            session_id = _most_active_session(events)

        elif metric == "error_count":
            q = base_q.where(Event.status == "failure")
            result = await db.execute(q)
            events = result.scalars().all()
            value = float(len(events))
            session_id = _most_active_session(events)

        elif metric == "session_duration":
            # Check for sessions running longer than threshold seconds
            duration_cutoff = datetime.now(timezone.utc) - timedelta(seconds=threshold)
            sess_q = await db.execute(
                select(SessionRecord)
                .where(SessionRecord.agent_id == rule.agent_id)
                .where(SessionRecord.killed_at.is_(None))
                .where(SessionRecord.ended_at.is_(None))
                .where(SessionRecord.started_at <= duration_cutoff)
            )
            long_sessions = sess_q.scalars().all()
            if long_sessions:
                s = long_sessions[0]
                duration = (datetime.now(timezone.utc) - s.started_at).total_seconds()
                value = duration
                session_id = s.id
            else:
                value = 0.0
                session_id = ""
        else:
            return False, 0.0, ""

    # Apply operator
    breached = _check_operator(operator, value, threshold)
    return breached, value, session_id


def _check_operator(operator: str, value: float, threshold: float) -> bool:
    if operator == "gt":
        return value > threshold
    elif operator == "lt":
        return value < threshold
    elif operator == "eq":
        return value == threshold
    elif operator == "gte":
        return value >= threshold
    elif operator == "lte":
        return value <= threshold
    return False


def _most_active_session(events: list) -> str:
    """Find the session with the most events."""
    if not events:
        return ""
    counts: dict[str, int] = {}
    for e in events:
        counts[e.session_id] = counts.get(e.session_id, 0) + 1
    return max(counts, key=counts.get)


def _in_cooldown(rule: AlertRule) -> bool:
    """Check if a rule is in its cooldown period."""
    last_fire = _cooldowns.get(rule.id)
    if not last_fire:
        return False
    elapsed = (datetime.now(timezone.utc) - last_fire).total_seconds()
    return elapsed < rule.cooldown_seconds


async def _fire_alert(rule: AlertRule, metric_value: float, session_id: str):
    """Execute alert actions."""
    if not session_id:
        return

    logger.info(f"ALERT FIRED: rule={rule.name} session={session_id} value={metric_value}")

    actions_taken = []

    for action in (rule.actions or []):
        action_type = action.get("type", "")

        if action_type == "dashboard_notification":
            actions_taken.append("dashboard_notification")

        elif action_type == "webhook":
            url = action.get("url", "")
            if url:
                await _send_webhook(url, rule, metric_value, session_id)
                actions_taken.append(f"webhook:{url}")

        elif action_type == "auto_kill":
            await _auto_kill(session_id, rule.name)
            actions_taken.append("auto_kill")

    # Record the alert
    async with async_session() as db:
        alert = Alert(
            rule_id=rule.id,
            session_id=session_id,
            agent_name="",
            metric_value=metric_value,
            threshold=float(rule.condition.get("threshold", 0)),
            actions_taken=actions_taken,
        )
        db.add(alert)
        await db.commit()


async def _send_webhook(url: str, rule: AlertRule, metric_value: float, session_id: str):
    """Send webhook notification with retry."""
    payload = {
        "alert_type": "bulwark_alert",
        "rule_name": rule.name,
        "session_id": session_id,
        "metric_value": metric_value,
        "threshold": rule.condition.get("threshold"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                resp = await client.post(url, json=payload, timeout=10.0)
                if resp.status_code < 400:
                    return
            except httpx.HTTPError:
                pass
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    logger.warning(f"Webhook delivery failed after 3 attempts: {url}")


async def _auto_kill(session_id: str, rule_name: str):
    """Automatically kill a session."""
    logger.info(f"AUTO-KILL: session={session_id} triggered by rule={rule_name}")

    async with async_session() as db:
        session = await db.get(SessionRecord, session_id)
        if session and not session.killed_at:
            session.killed_at = datetime.now(timezone.utc)
            await db.commit()
