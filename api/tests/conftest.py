"""Test fixtures for the Bulwark API."""

import hashlib
import os

import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Override DATABASE_URL before importing the app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.db import Base, Agent
from app.main import app
import app.db as db_module
import app.auth as auth_module
import app.routes.events as events_module
import app.routes.sessions as sessions_module
import app.routes.agents as agents_module
import app.routes.stats as stats_module
import app.routes.rules as rules_module
import app.routes.alerts as alerts_module
import app.routes.waitlist as waitlist_module
import app.routes.setup as setup_module
import app.evaluator as evaluator_module


TEST_API_KEY = "bwk_testkey123"
TEST_API_KEY_HASH = hashlib.sha256(TEST_API_KEY.encode()).hexdigest()

# All modules that do `from app.db import async_session`
_SESSION_MODULES = [
    db_module,
    auth_module,
    events_module,
    sessions_module,
    agents_module,
    stats_module,
    rules_module,
    alerts_module,
    waitlist_module,
    setup_module,
    evaluator_module,
]


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create a fresh in-memory database for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch async_session in every module that imported it
    for mod in _SESSION_MODULES:
        mod.async_session = session_factory

    # Seed test agent
    async with session_factory() as session:
        agent = Agent(
            id="test_agent_id",
            name="test-agent",
            api_key_hash=TEST_API_KEY_HASH,
        )
        session.add(agent)
        await session.commit()

    yield session_factory

    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing the API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def auth_headers():
    """Authorization headers for the test agent."""
    return {"Authorization": f"Bearer {TEST_API_KEY}"}
