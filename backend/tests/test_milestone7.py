import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from seed.load_seed import seed_database
from app.config import settings
from app.tools.events import log_event, get_all_events
from app.agents.orchestrator import execute_workflow_stage


@pytest.fixture(autouse=True)
async def setup_seed_data():
    await seed_database()


@pytest.mark.asyncio
async def test_analytics_summary_with_real_events():
    """Test BigQuery telemetry aggregation and recentEvents stream."""
    # Emit test events to verify live streaming
    await log_event(
        event_type="assessment_created",
        user_role="lecturer",
        assessment_id="asm-demo",
        duration_ms=45,
    )
    await log_event(
        event_type="paper_approved",
        user_role="moderator",
        assessment_id="asm-demo",
        duration_ms=120,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analytics/summary", headers={"X-Demo-Role": "lecturer"})
        assert resp.status_code == 200
        data = resp.json()

        # Verify KPI Metrics
        # Metrics are measured from stored data only (no placeholder floors)
        assert data["totalAssessments"] >= 1
        assert data["papersGenerated"] >= 0
        assert data["estimatedTimeSavedHours"] >= 0
        assert 0 <= data["acceptanceRatePercent"] <= 100
        assert len(data["flagsRaisedByType"]) == 7
        assert isinstance(data["timePerStage"], list)
        assert data["totalLoggedEvents"] >= 2

        # Verify Recent Events stream table
        assert "recentEvents" in data
        assert len(data["recentEvents"]) >= 2
        event_types = [e["event_type"] for e in data["recentEvents"]]
        assert "assessment_created" in event_types or "paper_approved" in event_types


@pytest.mark.asyncio
async def test_orchestrator_stage_execution():
    """Test Orchestrator sequential stage execution and event recording."""
    res = await execute_workflow_stage("solver", "asm-demo", run_id="run-orch-test")
    assert res["status"] == "success"
    assert res["runtime"] in ["local_adk", "agent_engine"]
    assert res["data"]["versionCount"] == 2
    assert res["data"]["solverStatus"] == "OPTIMAL"


@pytest.mark.asyncio
async def test_agent_engine_runtime_flag():
    """Test AGENT_RUNTIME configuration toggle resilience."""
    original_runtime = settings.AGENT_RUNTIME
    try:
        # Toggle to agent_engine without remote credentials -> gracefully falls back to local ADK
        settings.AGENT_RUNTIME = "agent_engine"
        res = await execute_workflow_stage("moderation", "asm-demo", run_id="run-agent-engine-test")
        assert res["status"] == "success"
    finally:
        settings.AGENT_RUNTIME = original_runtime
