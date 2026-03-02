"""One-time setup endpoint to seed the first API key on a fresh deploy."""

from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import hash_api_key
from app.db import async_session, Agent

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


class SetupRequest(BaseModel):
    token: str
    agent_name: str = "default"


@router.post("/setup")
@limiter.limit("3/hour")
async def first_time_setup(request: Request, body: SetupRequest):
    """Create the first agent and API key on a fresh deployment.

    Requires SETUP_TOKEN env var to be set. Once an agent exists,
    this endpoint is permanently disabled.
    """
    setup_token = os.getenv("SETUP_TOKEN")
    if not setup_token:
        raise HTTPException(
            status_code=404,
            detail="Setup is not available. Set SETUP_TOKEN env var to enable.",
        )

    if body.token != setup_token:
        raise HTTPException(status_code=403, detail="Invalid setup token.")

    async with async_session() as db:
        count = await db.execute(select(func.count(Agent.id)))
        if count.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail="Setup already completed. Agents exist.",
            )

        api_key = f"bwk_{secrets.token_hex(20)}"
        agent = Agent(
            name=body.agent_name,
            api_key_hash=hash_api_key(api_key),
        )
        db.add(agent)
        await db.commit()

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "api_key": api_key,
        "warning": "Store this key securely. It cannot be retrieved again. Remove SETUP_TOKEN env var after setup.",
    }
