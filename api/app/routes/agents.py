"""Agent listing endpoint for dashboard."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func

from app.auth import get_agent
from app.db import async_session, Agent, SessionRecord, Event

router = APIRouter()


class AgentInfo(BaseModel):
    id: str
    name: str
    active_sessions: int
    total_events_24h: int
    total_cost_24h: float


@router.get("/agents")
async def list_agents(agent: Agent = Depends(get_agent)):
    """List all agents with session and event stats."""
    async with async_session() as db:
        # Get all agents (for now, just the authenticated one)
        # In multi-tenant future, this would be scoped to org
        agents_list = [agent]

        result = []
        for a in agents_list:
            # Count active sessions
            active_q = await db.execute(
                select(func.count(SessionRecord.id))
                .where(SessionRecord.agent_id == a.id)
                .where(SessionRecord.ended_at.is_(None))
                .where(SessionRecord.killed_at.is_(None))
            )
            active_count = active_q.scalar() or 0

            # Count events in last 24h
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            events_q = await db.execute(
                select(func.count(Event.id))
                .join(SessionRecord, Event.session_id == SessionRecord.id)
                .where(SessionRecord.agent_id == a.id)
                .where(Event.created_at >= cutoff)
            )
            event_count = events_q.scalar() or 0

            # Sum cost in last 24h (from llm_call payloads)
            cost_q = await db.execute(
                select(Event.payload)
                .join(SessionRecord, Event.session_id == SessionRecord.id)
                .where(SessionRecord.agent_id == a.id)
                .where(Event.event_type == "llm_call")
                .where(Event.created_at >= cutoff)
            )
            total_cost = sum(
                (row[0] or {}).get("cost_usd", 0)
                for row in cost_q.all()
            )

            result.append(AgentInfo(
                id=a.id,
                name=a.name,
                active_sessions=active_count,
                total_events_24h=event_count,
                total_cost_24h=total_cost,
            ))

    return {"agents": result}
