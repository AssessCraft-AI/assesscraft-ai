import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "assesscraft"


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


@pytest.mark.asyncio
async def test_courses_list_and_seed():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/courses", headers={"x-demo-user": "lecturer@demo"})
    assert response.status_code == 200
    courses = response.json()
    assert len(courses) >= 1
    codes = [c["code"] for c in courses]
    assert "CS2040" in codes


@pytest.mark.asyncio
async def test_analytics_summary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/analytics/summary", headers={"x-demo-user": "lecturer@demo"})
    assert response.status_code == 200
    summary = response.json()
    assert "totalAssessments" in summary
    assert "flagsRaisedByType" in summary


@pytest.mark.asyncio
async def test_demo_headers_rejected_when_demo_auth_disabled():
    """With ENABLE_DEMO_AUTH off, demo headers/tokens must not authenticate anyone."""
    from app.config import settings

    original = settings.ENABLE_DEMO_AUTH
    settings.ENABLE_DEMO_AUTH = False
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            for headers in (
                {"x-demo-user": "lecturer@demo"},
                {"x-demo-role": "moderator"},
                {"Authorization": "Bearer demo-moderator-token"},
                {},
            ):
                resp = await ac.get("/courses", headers=headers)
                assert resp.status_code == 401, headers
    finally:
        settings.ENABLE_DEMO_AUTH = original
