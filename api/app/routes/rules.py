"""Alert rules CRUD endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.auth import get_agent
from app.db import async_session, AlertRule, Agent

router = APIRouter()


class ConditionSchema(BaseModel):
    metric: str
    operator: str
    threshold: float
    window_seconds: int = 300


class ActionSchema(BaseModel):
    type: str  # "webhook", "dashboard_notification", "auto_kill"
    url: Optional[str] = None


class ScopeSchema(BaseModel):
    agent_name: Optional[str] = None
    environment: Optional[str] = None


class CreateRuleRequest(BaseModel):
    name: str
    description: str = ""
    condition: ConditionSchema
    actions: list[ActionSchema]
    scope: ScopeSchema = ScopeSchema()
    cooldown_seconds: int = 300
    enabled: bool = True


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[ConditionSchema] = None
    actions: Optional[list[ActionSchema]] = None
    scope: Optional[ScopeSchema] = None
    cooldown_seconds: Optional[int] = None
    enabled: Optional[bool] = None


def rule_to_dict(r: AlertRule) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "enabled": r.enabled,
        "condition": r.condition,
        "actions": r.actions,
        "scope": r.scope,
        "cooldown_seconds": r.cooldown_seconds,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


@router.post("/rules")
async def create_rule(req: CreateRuleRequest, agent: Agent = Depends(get_agent)):
    """Create a new alert rule."""
    async with async_session() as db:
        rule = AlertRule(
            agent_id=agent.id,
            name=req.name,
            description=req.description,
            enabled=req.enabled,
            condition=req.condition.model_dump(),
            actions=[a.model_dump() for a in req.actions],
            scope=req.scope.model_dump(),
            cooldown_seconds=req.cooldown_seconds,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
    return rule_to_dict(rule)


@router.get("/rules")
async def list_rules(agent: Agent = Depends(get_agent)):
    """List all alert rules."""
    async with async_session() as db:
        result = await db.execute(
            select(AlertRule)
            .where(AlertRule.agent_id == agent.id)
            .order_by(AlertRule.created_at.desc())
        )
        rules = result.scalars().all()
    return {"rules": [rule_to_dict(r) for r in rules]}


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str, agent: Agent = Depends(get_agent)):
    """Get a single rule."""
    async with async_session() as db:
        rule = await db.get(AlertRule, rule_id)
        if not rule or rule.agent_id != agent.id:
            raise HTTPException(status_code=404, detail="Rule not found")
    return rule_to_dict(rule)


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, req: UpdateRuleRequest, agent: Agent = Depends(get_agent)):
    """Update an alert rule."""
    async with async_session() as db:
        rule = await db.get(AlertRule, rule_id)
        if not rule or rule.agent_id != agent.id:
            raise HTTPException(status_code=404, detail="Rule not found")

        if req.name is not None:
            rule.name = req.name
        if req.description is not None:
            rule.description = req.description
        if req.condition is not None:
            rule.condition = req.condition.model_dump()
        if req.actions is not None:
            rule.actions = [a.model_dump() for a in req.actions]
        if req.scope is not None:
            rule.scope = req.scope.model_dump()
        if req.cooldown_seconds is not None:
            rule.cooldown_seconds = req.cooldown_seconds
        if req.enabled is not None:
            rule.enabled = req.enabled

        rule.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(rule)
    return rule_to_dict(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, agent: Agent = Depends(get_agent)):
    """Delete an alert rule."""
    async with async_session() as db:
        rule = await db.get(AlertRule, rule_id)
        if not rule or rule.agent_id != agent.id:
            raise HTTPException(status_code=404, detail="Rule not found")
        await db.delete(rule)
        await db.commit()
    return {"deleted": True}


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, agent: Agent = Depends(get_agent)):
    """Toggle a rule's enabled state."""
    async with async_session() as db:
        rule = await db.get(AlertRule, rule_id)
        if not rule or rule.agent_id != agent.id:
            raise HTTPException(status_code=404, detail="Rule not found")
        rule.enabled = not rule.enabled
        rule.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(rule)
    return rule_to_dict(rule)
