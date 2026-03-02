"""Aggregate stats endpoint for dashboard."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func

from app.auth import get_agent
from app.db import async_session, Agent, SessionRecord, Event

router = APIRouter()


class StatsResponse(BaseModel):
    active_sessions: int
    total_agents: int
    events_per_minute: float
    cost_24h: float


@router.get("/stats", response_model=StatsResponse)
async def get_stats(agent: Agent = Depends(get_agent)):
    """Get aggregate stats for the dashboard."""
    async with async_session() as db:
        # Active sessions
        active_q = await db.execute(
            select(func.count(SessionRecord.id))
            .where(SessionRecord.agent_id == agent.id)
            .where(SessionRecord.ended_at.is_(None))
            .where(SessionRecord.killed_at.is_(None))
        )
        active_sessions = active_q.scalar() or 0

        # Events in last minute
        one_min_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
        epm_q = await db.execute(
            select(func.count(Event.id))
            .join(SessionRecord, Event.session_id == SessionRecord.id)
            .where(SessionRecord.agent_id == agent.id)
            .where(Event.created_at >= one_min_ago)
        )
        events_per_minute = epm_q.scalar() or 0

        # Cost in last 24h
        cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        cost_q = await db.execute(
            select(Event.payload)
            .join(SessionRecord, Event.session_id == SessionRecord.id)
            .where(SessionRecord.agent_id == agent.id)
            .where(Event.event_type == "llm_call")
            .where(Event.created_at >= cutoff_24h)
        )
        cost_24h = sum(
            (row[0] or {}).get("cost_usd", 0)
            for row in cost_q.all()
        )

    return StatsResponse(
        active_sessions=active_sessions,
        total_agents=1,  # Single-tenant for now
        events_per_minute=events_per_minute,
        cost_24h=cost_24h,
    )
