"""Who may read and change a paper or module, the moderation lock, and the guards added after the audit."""
import pytest
from httpx import AsyncClient, ASGITransport

from app import auth as auth_module
from app.api import documents
from app.config import settings
from app.main import app
from app.services.firestore import FirestoreService, db
from app.services.traces import tracker
from seed.load_seed import seed_database

LECTURER = {"X-Demo-Role": "lecturer"}  # owns CS2040 and asm-demo
MODERATOR = {"X-Demo-Role": "moderator"}  # CS2040's moderator, but asm-demo is not submitted yet
OTHER = {"Authorization": "Bearer tok-other-lect"}  # a second lecturer who owns nothing


@pytest.fixture(autouse=True)
async def setup(monkeypatch):
    await seed_database()
    await db.set("users", "other-lect", {"uid": "other-lect", "email": "other@uni.edu", "displayName": "Other", "roles": ["lecturer"]})
    await tracker.create_run(run_id="run-private", assessment_id="asm-demo")

    def fake_verify(token, *a, **k):
        if not token.startswith("tok-"):
            raise ValueError("bad token")
        return {"uid": token[4:], "email": f"{token[4:]}@uni.edu"}

    monkeypatch.setattr(auth_module.firebase_auth, "verify_id_token", fake_verify)


def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _ids(collection):
    return [d["id"] for d in await db.query(collection, filters=[("assessmentId", "==", "asm-demo")])]


def _paper_routes(item_id, flag_id, version_id):
    return [
        ("GET", "/assessments/asm-demo/items", None),
        ("GET", "/assessments/asm-demo/flags", None),
        ("GET", "/assessments/asm-demo/versions", None),
        ("GET", f"/assessments/asm-demo/versions/{version_id}/items", None),
        ("GET", "/assessments/asm-demo/equivalence", None),
        ("GET", "/assessments/asm-demo/blueprint", None),
        ("GET", "/assessments/asm-demo/export?format=keys&version=A&delivery=direct", None),
        ("GET", "/runs/run-private", None),
        ("POST", "/assessments/asm-demo/blueprint", None),
        ("POST", "/assessments/asm-demo/pool", None),
        ("POST", "/assessments/asm-demo/review", None),
        ("POST", "/assessments/asm-demo/assemble", None),
        ("PATCH", f"/items/{item_id}", {"key": "B"}),
        ("PATCH", f"/flags/{flag_id}", {"resolution": "accepted"}),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [OTHER, MODERATOR], ids=["other-lecturer", "unassigned-moderator"])
async def test_paper_is_invisible_to_non_owners(headers):
    """Every paper sub-route answers 404, like GET /assessments/{id}, so answer keys never leak."""
    item_id, flag_id, version_id = (await _ids("items"))[0], (await _ids("flags"))[0], (await _ids("versions"))[0]
    key_before = (await db.get("items", item_id))["key"]
    async with client() as c:
        for method, path, body in _paper_routes(item_id, flag_id, version_id):
            resp = await c.request(method, path, headers=headers, json=body)
            assert resp.status_code == 404, f"{method} {path} -> {resp.status_code}"
    assert (await db.get("items", item_id))["key"] == key_before


@pytest.mark.asyncio
async def test_owner_still_reads_their_paper():
    async with client() as c:
        for path in ("/assessments/asm-demo/items", "/runs/run-private", "/assessments/asm-demo/export?format=keys&version=A&delivery=direct"):
            assert (await c.get(path, headers=LECTURER)).status_code == 200, path


@pytest.mark.asyncio
async def test_paper_is_locked_in_moderation_and_after_approval():
    item_id = (await _ids("items"))[0]
    async with client() as c:
        assert (await c.post("/assessments/asm-demo/submit", headers=LECTURER)).status_code == 200
        assert (await c.patch(f"/items/{item_id}", headers=LECTURER, json={"key": "B"})).status_code == 409
        assert (await c.post("/assessments/asm-demo/assemble", headers=LECTURER)).status_code == 409

        # Changes requested reopens the paper for its examiner.
        await c.post("/assessments/asm-demo/decision", headers=MODERATOR, json={"decision": "changes_requested"})
        assert (await c.patch(f"/items/{item_id}", headers=LECTURER, json={"rationale": "fixed"})).status_code == 200

        assert (await c.post("/assessments/asm-demo/submit", headers=LECTURER)).status_code == 200
        await c.post("/assessments/asm-demo/decision", headers=MODERATOR, json={"decision": "approved"})
        assert (await c.patch(f"/items/{item_id}", headers=LECTURER, json={"key": "C"})).status_code == 409


@pytest.mark.asyncio
async def test_only_the_assigned_moderator_runs_the_qa_audit_while_in_moderation():
    async with client() as c:
        assert (await c.post("/assessments/asm-demo/moderation", headers=LECTURER)).status_code == 403
        assert (await c.post("/assessments/asm-demo/moderation", headers=MODERATOR)).status_code == 404  # not submitted to them, so the paper is invisible
        assert (await c.post("/assessments/asm-demo/submit", headers=LECTURER)).status_code == 200
        assert (await c.post("/assessments/asm-demo/moderation", headers=LECTURER)).status_code == 403
        assert (await c.post("/assessments/asm-demo/moderation", headers=MODERATOR)).status_code == 200
        await db.update("assessments", "asm-demo", {"status": "approved"})
        assert (await c.post("/assessments/asm-demo/moderation", headers=MODERATOR)).status_code == 409


@pytest.mark.asyncio
async def test_redeciding_a_flag_does_not_repeat_its_note():
    flag_id = (await _ids("flags"))[0]
    body = {"resolution": "dismissed", "detail": "Kept by lecturer after review"}
    async with client() as c:
        for _ in range(2):
            assert (await c.patch(f"/flags/{flag_id}", headers=LECTURER, json=body)).status_code == 200
    assert (await db.get("flags", flag_id))["detail"].count("Note: Kept by lecturer after review") == 1


@pytest.mark.asyncio
async def test_only_module_examiner_changes_module():
    async with client() as c:
        outcomes = {"clos": [], "topics": [], "confirmed": True}
        assert (await c.put("/courses/CS2040/outcomes", headers=OTHER, json=outcomes)).status_code == 403
        upload = {"file": ("notes.txt", b"hello", "text/plain")}
        assert (await c.post("/courses/CS2040/documents", headers=OTHER, files=upload)).status_code == 403
        assert (await c.post("/courses/CS2040/extract", headers=OTHER)).status_code == 403
        paper = {"courseId": "CS2040", "request": "Midterm"}
        assert (await c.post("/assessments", headers=OTHER, json=paper)).status_code == 403
        assert (await c.post("/assessments", headers=LECTURER, json={**paper, "courseId": "NOPE"})).status_code == 404
    assert (await db.get("courses", "CS2040"))["clos"], "CS2040 outcomes must be untouched"


@pytest.mark.asyncio
async def test_upload_size_limit(monkeypatch):
    monkeypatch.setattr(documents, "MAX_UPLOAD_BYTES", 10)
    async with client() as c:
        resp = await c.post("/courses/CS2040/documents", headers=LECTURER, files={"file": ("big.txt", b"x" * 11, "text/plain")})
        assert resp.status_code == 413


@pytest.mark.asyncio
async def test_export_of_missing_version_is_404_not_the_draft_pool():
    async with client() as c:
        resp = await c.get("/assessments/asm-demo/export?format=pdf&version=Z&delivery=direct", headers=LECTURER)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cloud_errors_are_not_swallowed():
    """A failed Firestore call must raise, not fall back to the in-memory store and report success."""

    class Broken:
        def collection(self, name):
            raise RuntimeError("firestore down")

    svc = FirestoreService.__new__(FirestoreService)
    svc._client = Broken()
    for call in (svc.get("users", "u"), svc.set("users", "u", {}), svc.query("users"), svc.delete("users", "u")):
        with pytest.raises(RuntimeError):
            await call


@pytest.mark.asyncio
async def test_strict_mode_never_falls_back_from_agent_engine(monkeypatch):
    from app.agents import orchestrator

    monkeypatch.setattr(settings, "AGENT_RUNTIME", "agent_engine")
    monkeypatch.setattr(settings, "AGENT_ENGINE_ID", "missing-engine")
    monkeypatch.setattr(settings, "STRICT_MODE", True)
    monkeypatch.setattr(orchestrator, "_engine_client", None)
    with pytest.raises(RuntimeError, match="unreachable"):
        await orchestrator.execute_workflow_stage("solver", "asm-demo", run_id="run-strict")


@pytest.mark.asyncio
async def test_internal_errors_do_not_leak_details(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("projects/secret-project/databases/(default) exploded")

    monkeypatch.setattr(db, "query", boom)
    async with client() as c:
        resp = await c.get("/courses", headers=LECTURER)
    assert resp.status_code == 500 and "secret-project" not in resp.text


@pytest.mark.asyncio
async def test_modules_scoped_to_assignee_and_admin_only_create():
    async with client() as c:
        assert "CS2040" in [m["code"] for m in (await c.get("/courses", headers=LECTURER)).json()]
        assert "CS2040" in [m["code"] for m in (await c.get("/courses", headers=MODERATOR)).json()]
        assert (await c.get("/courses", headers=OTHER)).json() == []
        resp = await c.post("/courses", headers=LECTURER, json={"code": "IT7777", "title": "X"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_paper_needs_extracted_outcomes():
    course = await db.get("courses", "CS2040")
    await db.set("courses", "CS2040", {**course, "clos": [], "topics": []})
    async with client() as c:
        resp = await c.post("/assessments", headers=LECTURER, json={"courseId": "CS2040", "request": "Midterm"})
    assert resp.status_code == 400 and "outcomes" in resp.json()["detail"]

    from app.agents.blueprint import run_blueprint_agent
    with pytest.raises(ValueError, match="no extracted learning outcomes"):
        await run_blueprint_agent("asm-demo")
    async with client() as c:
        assert (await c.post("/assessments/asm-demo/blueprint", headers=LECTURER)).status_code == 400


@pytest.mark.asyncio
async def test_only_paper_lecturer_deletes_unlocked_paper():
    async with client() as c:
        assert (await c.delete("/assessments/asm-demo", headers=OTHER)).status_code == 404
        assert (await c.delete("/assessments/asm-demo", headers=MODERATOR)).status_code in (403, 404)

        await db.update("assessments", "asm-demo", {"status": "in_moderation"})
        assert (await c.delete("/assessments/asm-demo", headers=LECTURER)).status_code == 409

        await db.update("assessments", "asm-demo", {"status": "assembled"})
        assert (await c.delete("/assessments/asm-demo", headers=LECTURER)).status_code == 204
    assert await db.get("assessments", "asm-demo") is None
    assert await db.get("blueprints", "asm-demo") is None
    assert not await _ids("items") and not await _ids("versions")
    audit = await db.query("audit", filters=[("entityId", "==", "asm-demo")])
    assert any(a["action"] == "delete_assessment" for a in audit)
