"""API key authentication."""

from __future__ import annotations

import hashlib
import os

from fastapi import Header, HTTPException, Depends
from sqlalchemy import select

from app.db import async_session, Agent


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


async def get_agent(authorization: str = Header(...)) -> Agent:
    """Validate API key and return the associated agent."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    api_key = authorization.removeprefix("Bearer ").strip()
    key_hash = hash_api_key(api_key)

    async with async_session() as session:
        result = await session.execute(
            select(Agent).where(Agent.api_key_hash == key_hash)
        )
        agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return agent
