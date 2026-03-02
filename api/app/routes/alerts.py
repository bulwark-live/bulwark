"""Alert history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func

from app.auth import get_agent
from app.db import async_session, Alert, AlertRule, Agent

router = APIRouter()


def alert_to_dict(a: Alert) -> dict:
    return {
        "id": a.id,
        "rule_id": a.rule_id,
        "session_id": a.session_id,
        "agent_name": a.agent_name,
        "metric_value": a.metric_value,
        "threshold": a.threshold,
        "actions_taken": a.actions_taken,
        "acknowledged": a.acknowledged,
        "created_at": a.created_at.isoformat(),
    }


@router.get("/alerts")
async def list_alerts(agent: Agent = Depends(get_agent)):
    """List all fired alerts, newest first."""
    async with async_session() as db:
        result = await db.execute(
            select(Alert)
            .join(AlertRule, Alert.rule_id == AlertRule.id)
            .where(AlertRule.agent_id == agent.id)
            .order_by(Alert.created_at.desc())
            .limit(100)
        )
        alerts = result.scalars().all()

        # Enrich with rule names
        enriched = []
        for a in alerts:
            rule = await db.get(AlertRule, a.rule_id)
            d = alert_to_dict(a)
            d["rule_name"] = rule.name if rule else "Unknown"
            enriched.append(d)

    return {"alerts": enriched}


@router.get("/alerts/unread")
async def unread_count(agent: Agent = Depends(get_agent)):
    """Get count of unacknowledged alerts."""
    async with async_session() as db:
        result = await db.execute(
            select(func.count(Alert.id))
            .join(AlertRule, Alert.rule_id == AlertRule.id)
            .where(AlertRule.agent_id == agent.id)
            .where(Alert.acknowledged == False)
        )
        count = result.scalar() or 0
    return {"unread": count}


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(alert_id: str, agent: Agent = Depends(get_agent)):
    """Acknowledge an alert."""
    async with async_session() as db:
        alert = await db.get(Alert, alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Verify ownership
        rule = await db.get(AlertRule, alert.rule_id)
        if not rule or rule.agent_id != agent.id:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert.acknowledged = True
        await db.commit()
    return {"acknowledged": True}
