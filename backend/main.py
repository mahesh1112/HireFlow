"""
HireFlow FastAPI Application Entry Point
"""
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import text
from app.config import settings
from app.database import create_tables, AsyncSessionLocal, engine
from app.api import auth, resumes, jobs, screening, admin, units

logger = structlog.get_logger()


async def _add_missing_columns() -> None:
    """Idempotent: add columns that create_all cannot add to existing tables."""
    ddl = [
        # job_descriptions lifecycle columns
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS business_unit_id VARCHAR(36) REFERENCES business_units(id)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS experience VARCHAR(20)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS employee_type VARCHAR(50)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS location_office VARCHAR(100)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS remote_job BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS hiring_leads JSON DEFAULT '[]'",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS recruiter_id VARCHAR(36) REFERENCES users(id)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS valid_till TIMESTAMPTZ",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'",
        # resumes multi-unit + BYTEA storage columns
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS unit_id VARCHAR(36) REFERENCES business_units(id)",
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS job_position_id VARCHAR(36) REFERENCES job_descriptions(job_id)",
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS resume_file BYTEA",
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS file_mimetype VARCHAR(50)",
        # Allow NULL file_path (BYTEA storage replaces disk files)
        "ALTER TABLE resumes ALTER COLUMN file_path DROP NOT NULL",
        # Content hash for deduplication
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)",
    ]
    try:
        async with engine.begin() as conn:
            for stmt in ddl:
                await conn.execute(text(stmt))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_resumes_content_hash ON resumes (content_hash)"
            ))
        logger.info("All missing columns verified")
    except Exception as exc:
        logger.warning("Column migration warning", error=str(exc))


async def seed_business_units() -> None:
    """Idempotently seed the 3 business units on every startup."""
    try:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from app.models.unit import BusinessUnit

        UNITS = [
            {"id": "00000000-0000-0000-0000-000000000001", "unit_slug": "dpu",           "unit_name": "Digital Publishing Unit"},
            {"id": "00000000-0000-0000-0000-000000000002", "unit_slug": "resource_mgmt", "unit_name": "Resource Management Group"},
            {"id": "00000000-0000-0000-0000-000000000003", "unit_slug": "delivery",      "unit_name": "Delivery Unit"},
        ]
        async with AsyncSessionLocal() as db:
            for u in UNITS:
                stmt = pg_insert(BusinessUnit).values(**u).on_conflict_do_nothing(
                    index_elements=["unit_slug"]
                )
                await db.execute(stmt)
            await db.commit()
        logger.info("Business units seeded")
    except Exception as exc:
        logger.warning("Business unit seeding failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting HireFlow API", version=settings.APP_VERSION, env=settings.ENVIRONMENT)

    # Create database tables
    try:
        await create_tables()
        logger.info("Database tables ready")
    except Exception as exc:
        logger.warning("Database table creation failed (may already exist)", error=str(exc))

    # Seed business units
    await seed_business_units()

    # Add missing columns to existing tables (idempotent)
    await _add_missing_columns()

    yield

    logger.info("Shutting down HireFlow API")


app = FastAPI(
    title="HireFlow API",
    description="Intelligent Resume Screening & Candidate Shortlisting System",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware (simple in-memory — use redis-rate-limit in production)
from collections import defaultdict
from time import time as _time

_request_counts: dict = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        now = _time()
        window = 60  # 1 minute
        max_requests = 100

        # Clean old entries
        _request_counts[client_ip] = [
            t for t in _request_counts[client_ip] if now - t < window
        ]

        if len(_request_counts[client_ip]) >= max_requests:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Max 100 requests/minute."},
            )

        _request_counts[client_ip].append(now)

    return await call_next(request)


# ─── Global Error Handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(screening.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(units.router, prefix="/api")


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/health", tags=["Health"])
async def api_health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
