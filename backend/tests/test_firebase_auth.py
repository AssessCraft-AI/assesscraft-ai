"""Firebase sign-in: role resolution, domain allow-list, /me, STRICT_MODE and LLM config."""
import pytest
from httpx import AsyncClient, ASGITransport

from app import auth as auth_module
from app.config import settings
from app.main import app
from app.services.firestore import db


@pytest.fixture
def firebase_only(monkeypatch):
    """Demo auth off; verify_id_token returns whatever the test sets in `claims`."""
    monkeypatch.setattr(settings, "ENABLE_DEMO_AUTH", False)
    claims = {}

    def fake_verify(token, *a, **k):
        if token != "good-token":
            raise ValueError("bad token")
        return dict(claims)

    monkeypatch.setattr(auth_module.firebase_auth, "verify_id_token", fake_verify)
    return claims


async def _get(path, token="good-token"):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        return await ac.get(path, headers={"Authorization": f"Bearer {token}"})


@pytest.mark.asyncio
async def test_invalid_token_is_401(firebase_only):
    assert (await _get("/me", token="nope")).status_code == 401


@pytest.mark.asyncio
async def test_role_comes_from_custom_claim(firebase_only):
    firebase_only.update(uid="u-claim", email="someone@uni.edu", role="moderator")
    resp = await _get("/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "moderator"


@pytest.mark.asyncio
async def test_role_falls_back_to_users_record(firebase_only):
    await db.set("users", "u-rec", {"uid": "u-rec", "email": "x@uni.edu", "displayName": "Rec", "role": "lecturer"})
    firebase_only.update(uid="u-rec", email="x@uni.edu")
    assert (await _get("/me")).json()["role"] == "lecturer"


@pytest.mark.asyncio
async def test_email_never_elevates_role(firebase_only):
    """Regression: an email containing 'moderator' or 'qa' must NOT grant that role."""
    firebase_only.update(uid="u-evil", email="moderator-qa@gmail.com")
    assert (await _get("/me")).status_code == 403


@pytest.mark.asyncio
async def test_unknown_claim_value_is_ignored(firebase_only):
    firebase_only.update(uid="u-bogus", email="a@uni.edu", role="superuser")
    assert (await _get("/me")).status_code == 403


@pytest.mark.asyncio
async def test_account_without_role_is_refused_unless_default_role_set(firebase_only, monkeypatch):
    """A self-registered Firebase account gets nothing until an admin assigns a role."""
    firebase_only.update(uid="u-new", email="stranger@gmail.com")
    resp = await _get("/me")
    assert resp.status_code == 403 and "administrator" in resp.json()["detail"]
    monkeypatch.setattr(settings, "DEFAULT_ROLE", "lecturer")
    assert (await _get("/me")).json()["role"] == "lecturer"


@pytest.mark.asyncio
async def test_disabled_account_is_refused(firebase_only):
    await db.set("users", "u-off", {"uid": "u-off", "email": "off@uni.edu", "displayName": "Off", "roles": ["lecturer"], "disabled": True})
    firebase_only.update(uid="u-off", email="off@uni.edu")
    assert (await _get("/me")).status_code == 403


@pytest.mark.asyncio
async def test_domain_allow_list(firebase_only, monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_EMAIL_DOMAINS", "uni.edu")
    firebase_only.update(uid="u1", email="a@uni.edu", email_verified=True, role="lecturer")
    assert (await _get("/me")).status_code == 200
    firebase_only.update(uid="u2", email="a@gmail.com", email_verified=True)
    assert (await _get("/me")).status_code == 403
    firebase_only.update(uid="u3", email="a@uni.edu", email_verified=False)
    assert (await _get("/me")).status_code == 403


@pytest.mark.asyncio
async def test_lecturer_cannot_use_moderator_endpoint(firebase_only):
    firebase_only.update(uid="u-lect", email="l@uni.edu", role="lecturer")
    resp = await _get("/health/deep")  # admin-only
    assert resp.status_code == 403


def test_llm_configured_by_backend(monkeypatch):
    from app.tools import similarity

    monkeypatch.setattr(settings, "LLM_BACKEND", "openrouter")
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    assert similarity.llm_configured() is False
    monkeypatch.setattr(settings, "LLM_API_KEY", "k")
    assert similarity.llm_configured() is True
    monkeypatch.setattr(settings, "LLM_BACKEND", "vertex")
    monkeypatch.setattr(settings, "GCP_PROJECT_ID", "")
    assert similarity.llm_configured() is False


def test_check_llm_reports_unconfigured(monkeypatch):
    from app.tools import similarity

    monkeypatch.setattr(similarity, "_llm_client", None)
    monkeypatch.setattr(settings, "LLM_BACKEND", "openrouter")
    monkeypatch.setattr(settings, "LLM_API_KEY", "")
    result = similarity.check_llm()
    assert result["ok"] is False and "not configured" in result["error"]


def test_strict_mode_forbids_fallback_content(monkeypatch):
    from app.tools.similarity import require_llm_or_fallback

    monkeypatch.setattr(settings, "STRICT_MODE", False)
    require_llm_or_fallback("x")  # no raise
    monkeypatch.setattr(settings, "STRICT_MODE", True)
    with pytest.raises(RuntimeError):
        require_llm_or_fallback("x")


@pytest.mark.asyncio
async def test_strict_startup_fails_without_cloud(monkeypatch):
    from app.main import lifespan

    monkeypatch.setattr(settings, "STRICT_MODE", True)
    monkeypatch.setattr(settings, "ENABLE_DEMO_AUTH", False)
    with pytest.raises(RuntimeError, match="STRICT_MODE startup checks failed"):
        async with lifespan(app):
            pass
