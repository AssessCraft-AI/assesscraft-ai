import logging
import sys
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Request
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.auth import require_role
from app.models import Course, CLO, Topic, User
from app.tools.similarity import check_llm, llm_configured
from app.services.firestore import db, _IN_MEMORY_STORE
from app.api import (
    courses,
    assessments,
    documents,
    blueprints,
    items,
    flags,
    versions,
    moderation,
    exports,
    assistant,
    runs,
    analytics,
    me,
    admin,
    notifications,
)

# Structured logging setup
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", "message":"%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("assesscraft")


# Helper to ensure seed data exists
def seed_default_data():
    if "CS2040" not in _IN_MEMORY_STORE.get("courses", {}):
        default_course = Course(
            id="CS2040",
            code="CS2040",
            title="Database Systems",
            ownerUid="demo-lecturer-uid",
            moderatorUid="demo-moderator-uid",
            confirmed=True,
            clos=[
                CLO(id="CLO1", text="Design relational database schemas from conceptual models using ER diagrams and functional dependencies.", bloomLevel="create"),
                CLO(id="CLO2", text="Write efficient declarative SQL queries including multi-table joins, subqueries, and window functions.", bloomLevel="apply"),
                CLO(id="CLO3", text="Analyze transaction isolation levels, concurrency anomalies (dirty reads, phantoms), and ACID guarantees.", bloomLevel="analyse"),
                CLO(id="CLO4", text="Evaluate B+ tree indexing strategies and query execution plans for query performance tuning.", bloomLevel="evaluate"),
                CLO(id="CLO5", text="Normalize relational relations up to Boyce-Codd Normal Form (BCNF) and 3NF.", bloomLevel="apply"),
            ],
            topics=[
                Topic(id="t1", name="Entity-Relationship (ER) Modeling", cloIds=["CLO1"]),
                Topic(id="t2", name="Relational Algebra & Schema Design", cloIds=["CLO1", "CLO5"]),
                Topic(id="t3", name="SQL Fundamentals & Complex Joins", cloIds=["CLO2"]),
                Topic(id="t4", name="Subqueries & Aggregations", cloIds=["CLO2"]),
                Topic(id="t5", name="Transactions & Concurrency Control (ACID)", cloIds=["CLO3"]),
                Topic(id="t6", name="B+ Tree Indexing & Query Tuning", cloIds=["CLO4"]),
                Topic(id="t7", name="Normalization (1NF, 2NF, 3NF, BCNF)", cloIds=["CLO5"]),
                Topic(id="t8", name="Crash Recovery & Write-Ahead Logging", cloIds=["CLO3"]),
            ],
        )
        if "courses" not in _IN_MEMORY_STORE:
            _IN_MEMORY_STORE["courses"] = {}
        _IN_MEMORY_STORE["courses"]["CS2040"] = default_course.model_dump()

seed_default_data()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AssessCraft AI Backend starting up...")
    if settings.STRICT_MODE:
        problems = []
        if not db.is_cloud:
            problems.append("Firestore is not connected (check GCP_PROJECT_ID and credentials)")
        llm = check_llm()
        if not llm["ok"]:
            problems.append(f"LLM check failed: {llm}")
        if settings.ENABLE_DEMO_AUTH:
            problems.append("ENABLE_DEMO_AUTH must be false in STRICT_MODE")
        if "*" in settings.CORS_ORIGINS:
            problems.append("CORS_ORIGINS must not be '*' in STRICT_MODE")
        if problems:
            raise RuntimeError("STRICT_MODE startup checks failed: " + "; ".join(problems))
        logger.info("STRICT_MODE startup checks passed")
    if settings.ENABLE_DEMO_AUTH:
        # Demo personas need users/{uid} records for the admin dashboard and moderator assignments,
        # even when the (slow) full demo seed is off. Existing records keep any admin changes.
        from app.auth import DEMO_USERS
        for demo_user in DEMO_USERS.values():
            if not await db.get("users", demo_user.uid):
                await db.set("users", demo_user.uid, demo_user.model_dump())
    if settings.SEED_ON_STARTUP:
        seed_default_data()
        try:
            from seed.load_seed import seed_database
            await seed_database()
        except Exception as e:
            logger.warning(f"Seed database initialization note: {e}")
    yield
    logger.info("AssessCraft AI Backend shutting down...")


app = FastAPI(
    title="AssessCraft AI API",
    description="Agentic Assessment Copilot for Academic Assessment Work (Google Cloud AI Builder Cup 2026)",
    version="0.1.0",
    lifespan=lifespan,
)

# Global Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    run_id = request.headers.get("x-run-id", "-")
    logger.info(f"Incoming {request.method} {request.url.path} | runId: {run_id}")
    try:
        return await call_next(request)
    except Exception as e:
        # Unhandled errors would otherwise skip CORS headers and surface in the browser as "Failed to fetch".
        logger.exception(f"Unhandled error on {request.method} {request.url.path}")
        # Generic body: Google client errors carry project ids and paths; the details are in the log above.
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if "*" not in settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)  # added last so it wraps log_requests and also covers the 500 above


# Health and Root Endpoints
@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "region": settings.GCP_REGION,
        "model": settings.LLM_MODEL,
        "agentRuntime": settings.AGENT_RUNTIME,
        "datastore": "cloud_firestore" if db.is_cloud else "in_memory_resilient",
        "llmBackend": settings.LLM_BACKEND,
        "llmConfigured": llm_configured(),
        "strictMode": settings.STRICT_MODE,
        "demoAuth": settings.ENABLE_DEMO_AUTH,
    }


@app.get("/health/deep", tags=["system"])
async def deep_health_check(current_user: User = Depends(require_role(["admin"]))):
    """Live connectivity check (one tiny LLM generate + embed call). Admin only: it costs tokens."""
    return {"llm": await run_in_threadpool(check_llm), "datastore": "cloud_firestore" if db.is_cloud else "in_memory_resilient"}


@app.get("/", tags=["system"])
async def root():
    return {
        "name": "AssessCraft AI API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


# Include Routers
app.include_router(courses.router)
app.include_router(assessments.router)
app.include_router(documents.router)
app.include_router(documents.extract_router)
app.include_router(blueprints.router)
app.include_router(items.router)
app.include_router(flags.router)
app.include_router(versions.router)
app.include_router(moderation.router)
app.include_router(exports.router)
app.include_router(assistant.router)
app.include_router(runs.router)
app.include_router(analytics.router)
app.include_router(me.router)
app.include_router(admin.router)
app.include_router(notifications.router)
