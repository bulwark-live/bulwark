"""Event ingestion and feed endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.auth import get_agent
from app.db import async_session, Event, SessionRecord, Agent

router = APIRouter()


class EventPayload(BaseModel):
    event_id: str
    session_id: str
    agent_name: str
    environment: str = "production"
    event_type: str
    timestamp: str
    duration_ms: int | None = None
    status: str = "success"
    # All other fields go into payload
    model_config = {"extra": "allow"}


class BatchRequest(BaseModel):
    events: list[EventPayload]


class BatchResponse(BaseModel):
    accepted: int
    errors: int


@router.post("/events/batch", response_model=BatchResponse)
async def ingest_events(batch: BatchRequest, agent: Agent = Depends(get_agent)):
    """Ingest a batch of telemetry events from the SDK."""
    accepted = 0
    errors = 0

    async with async_session() as db:
        for evt in batch.events:
            try:
                # Ensure session exists (upsert)
                session_id = evt.session_id
                existing = await db.get(SessionRecord, session_id)
                if not existing:
                    db.add(SessionRecord(
                        id=session_id,
                        agent_id=agent.id,
                        environment=evt.environment,
                    ))

                # Extract extra fields as payload
                base_fields = {"event_id", "session_id", "agent_name", "environment",
                               "event_type", "timestamp", "duration_ms", "status"}
                payload = {k: v for k, v in evt.model_dump().items() if k not in base_fields}

                ts = datetime.fromisoformat(evt.timestamp)

                db.add(Event(
                    id=evt.event_id.removeprefix("evt_"),
                    session_id=session_id,
                    event_type=evt.event_type,
                    timestamp=ts,
                    duration_ms=evt.duration_ms,
                    status=evt.status,
                    payload=payload,
                ))
                accepted += 1
            except Exception:
                errors += 1

        await db.commit()

    return BatchResponse(accepted=accepted, errors=errors)


@router.get("/events")
async def list_events(
    agent: Agent = Depends(get_agent),
    since: Optional[str] = Query(None, description="ISO timestamp to fetch events after"),
    limit: int = Query(100, ge=1, le=500),
    session_id: Optional[str] = Query(None),
):
    """List events across all sessions, newest first. Used by dashboard event feed."""
    async with async_session() as db:
        q = (
            select(Event)
            .join(SessionRecord, Event.session_id == SessionRecord.id)
            .where(SessionRecord.agent_id == agent.id)
        )

        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                q = q.where(Event.timestamp > since_dt)
            except ValueError:
                pass

        if session_id:
            q = q.where(Event.session_id == session_id)

        q = q.order_by(Event.timestamp.desc()).limit(limit)
        result = await db.execute(q)
        events = result.scalars().all()

    # Return in chronological order (reversed from query)
    return {
        "events": [
            {
                "id": e.id,
                "session_id": e.session_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat(),
                "duration_ms": e.duration_ms,
                "status": e.status,
                "payload": e.payload,
            }
            for e in reversed(events)
        ]
    }
