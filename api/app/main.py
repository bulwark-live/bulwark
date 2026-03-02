"""Bulwark API — Real-time monitoring and kill switch for AI agents."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.db import engine, Base
from app.routes import events, sessions, health, agents, stats, rules, alerts, waitlist, setup
from app.evaluator import evaluate_rules


# --- Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)


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

app.state.limiter = limiter


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


# --- Security Headers Middleware ---

MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Reject oversized request bodies
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=413, content={"detail": "Request body too large"}
        )

    response: Response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if os.getenv("ENVIRONMENT") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# --- CORS ---

_default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://bulwark.live",
    "https://app.bulwark.live",
]
_extra_origins = os.getenv("CORS_ORIGINS", "").split(",")
_origins = _default_origins + [o.strip() for o in _extra_origins if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
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
app.include_router(waitlist.router, prefix="/v1")
app.include_router(setup.router, prefix="/v1")
