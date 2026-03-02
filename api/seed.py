"""Seed script — create a test agent with an API key."""

import asyncio
import secrets

from app.db import engine, Base, async_session, Agent
from app.auth import hash_api_key


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api_key = f"bwk_{secrets.token_hex(16)}"

    async with async_session() as db:
        agent = Agent(
            name="demo-agent",
            api_key_hash=hash_api_key(api_key),
        )
        db.add(agent)
        await db.commit()
        print(f"Agent created: {agent.name} (id: {agent.id})")

    print(f"API Key: {api_key}")
    print("Save this key — it won't be shown again.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
