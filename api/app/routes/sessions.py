"""Session management endpoints — including kill switch."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.auth import get_agent
from app.db import async_session, SessionRecord, Event, Agent

router = APIRouter()


class SessionSummary(BaseModel):
    id: str
    agent_name: str
    environment: str
    started_at: str
    ended_at: str | None
    killed_at: str | None
    event_count: int


class SessionStatus(BaseModel):
    session_id: str
    killed: bool
    killed_at: str | None = None


class KillResponse(BaseModel):
    session_id: str
    killed_at: str


@router.get("/sessions")
async def list_sessions(agent: Agent = Depends(get_agent)):
    """List all sessions for the authenticated agent."""
    async with async_session() as db:
        result = await db.execute(
            select(SessionRecord)
            .where(SessionRecord.agent_id == agent.id)
            .order_by(SessionRecord.started_at.desc())
            .limit(100)
        )
        sessions = result.scalars().all()

        summaries = []
        for s in sessions:
            event_result = await db.execute(
                select(Event).where(Event.session_id == s.id)
            )
            event_count = len(event_result.scalars().all())

            summaries.append(SessionSummary(
                id=s.id,
                agent_name=agent.name,
                environment=s.environment,
                started_at=s.started_at.isoformat(),
                ended_at=s.ended_at.isoformat() if s.ended_at else None,
                killed_at=s.killed_at.isoformat() if s.killed_at else None,
                event_count=event_count,
            ))

    return {"sessions": summaries}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, agent: Agent = Depends(get_agent)):
    """Get session detail with event timeline."""
    async with async_session() as db:
        session = await db.get(SessionRecord, session_id)
        if not session or session.agent_id != agent.id:
            raise HTTPException(status_code=404, detail="Session not found")

        result = await db.execute(
            select(Event)
            .where(Event.session_id == session_id)
            .order_by(Event.timestamp)
        )
        events = result.scalars().all()

    return {
        "session": {
            "id": session.id,
            "environment": session.environment,
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "killed_at": session.killed_at.isoformat() if session.killed_at else None,
        },
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat(),
                "duration_ms": e.duration_ms,
                "status": e.status,
                "payload": e.payload,
            }
            for e in events
        ],
    }


@router.get("/sessions/{session_id}/status", response_model=SessionStatus)
async def session_status(session_id: str):
    """Check if a session has been killed. Used by SDK kill switch polling.

    Note: No auth required — SDK polls this with session_id.
    """
    async with async_session() as db:
        session = await db.get(SessionRecord, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    return SessionStatus(
        session_id=session.id,
        killed=session.killed_at is not None,
        killed_at=session.killed_at.isoformat() if session.killed_at else None,
    )


@router.post("/sessions/{session_id}/kill", response_model=KillResponse)
async def kill_session(session_id: str, agent: Agent = Depends(get_agent)):
    """Kill a running agent session. The agent's SDK will detect this and exit."""
    async with async_session() as db:
        session = await db.get(SessionRecord, session_id)
        if not session or session.agent_id != agent.id:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.killed_at:
            return KillResponse(
                session_id=session.id,
                killed_at=session.killed_at.isoformat(),
            )

        now = datetime.now(timezone.utc)
        session.killed_at = now
        await db.commit()

    return KillResponse(session_id=session.id, killed_at=now.isoformat())
