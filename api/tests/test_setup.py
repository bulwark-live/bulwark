"""Tests for one-time setup endpoint."""

import os
from unittest.mock import patch

from sqlalchemy import delete

from app.db import Agent


SETUP_TOKEN = "test-setup-secret-123"


async def test_setup_creates_first_agent(client, setup_db):
    """First-time setup on empty DB should create agent and return API key."""
    # Remove the seeded test agent so DB is truly empty
    async with setup_db() as db:
        await db.execute(delete(Agent))
        await db.commit()

    with patch.dict(os.environ, {"SETUP_TOKEN": SETUP_TOKEN}):
        resp = await client.post(
            "/v1/setup",
            json={"token": SETUP_TOKEN, "agent_name": "bulwark-prod"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["api_key"].startswith("bwk_")
        assert data["agent_name"] == "bulwark-prod"
        assert "agent_id" in data

        # Verify the new key actually works
        new_headers = {"Authorization": f"Bearer {data['api_key']}"}
        agents_resp = await client.get("/v1/agents", headers=new_headers)
        assert agents_resp.status_code == 200


async def test_setup_rejects_when_agents_exist(client):
    """Once agents exist, setup returns 409."""
    with patch.dict(os.environ, {"SETUP_TOKEN": SETUP_TOKEN}):
        resp = await client.post(
            "/v1/setup",
            json={"token": SETUP_TOKEN, "agent_name": "bulwark-prod"},
        )
        assert resp.status_code == 409


async def test_setup_wrong_token(client):
    with patch.dict(os.environ, {"SETUP_TOKEN": SETUP_TOKEN}):
        resp = await client.post(
            "/v1/setup",
            json={"token": "wrong-token", "agent_name": "test"},
        )
        assert resp.status_code == 403


async def test_setup_no_token_configured(client):
    """When SETUP_TOKEN env var is not set, endpoint returns 404 (or 429 if rate-limited)."""
    with patch.dict(os.environ, {}, clear=False):
        env = os.environ.copy()
        env.pop("SETUP_TOKEN", None)
        with patch.dict(os.environ, env, clear=True):
            resp = await client.post(
                "/v1/setup",
                json={"token": "anything", "agent_name": "test"},
            )
            # 404 normally, 429 if rate limiter fires first (shared across tests)
            assert resp.status_code in (404, 429)
