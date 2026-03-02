"""Bulwark API — Real-time monitoring and kill switch for AI agents."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine, Base
from app.routes import events, sessions, health, agents, stats, rules, alerts
from app.evaluator import evaluate_rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start alert evaluation engine
    evaluator_task = asyncio.create_task(evaluate_rules())

    yield

    evaluator_task.cancel()
    await engine.dispose()


app = FastAPI(
    title="Bulwark API",
    description="The wall between AI agents and catastrophe.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(events.router, prefix="/v1")
app.include_router(sessions.router, prefix="/v1")
app.include_router(agents.router, prefix="/v1")
app.include_router(stats.router, prefix="/v1")
app.include_router(rules.router, prefix="/v1")
app.include_router(alerts.router, prefix="/v1")
