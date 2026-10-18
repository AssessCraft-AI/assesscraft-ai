"""Admin-managed accounts, per-module moderator assignment, submission, notifications and the decision loop."""
import itertools

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services import identity
from app.services.firestore import db
from seed.load_seed import seed_database

ADMIN = {"X-Demo-Role": "admin"}
LECTURER = {"X-Demo-Role": "lecturer"}
MODERATOR = {"X-Demo-Role": "moderator"}

_uids = itertools.count(1)


@pytest.fixture(autouse=True)
async def setup(monkeypatch):
    await seed_database()

    async def fake_create_account(email, password, display_name, role):
        return f"fb-uid-{next(_uids)}"

    async def fake_update_account(uid, **changes):
        return None

    monkeypatch.setattr(identity, "create_account", fake_create_account)
    monkeypatch.setattr(identity, "update_account", fake_update_account)


def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _notes(c, headers):
    resp = await c.get("/notifications", headers=headers)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_only_admin_can_manage_users():
    async with client() as c:
        assert (await c.get("/admin/users", headers=LECTURER)).status_code == 403
        assert (await c.get("/admin/users", headers=MODERATOR)).status_code == 403
        resp = await c.get("/admin/users", headers=ADMIN)
        assert resp.status_code == 200
        emails = {u["email"] for u in resp.json()}
        assert {"admin@demo", "lecturer@demo", "moderator@demo"} <= emails


@pytest.mark.asyncio
async def test_admin_creates_users_and_assigns_moderator():
    async with client() as c:
        mod = await c.post(
            "/admin/users",
            headers=ADMIN,
            json={"email": "Mod.One@Uni.edu", "displayName": "Mod One", "role": "moderator", "password": "secret12"},
        )
        assert mod.status_code == 201, mod.text
        mod = mod.json()
        assert mod["email"] == "mod.one@uni.edu" and mod["authProvisioned"] is True

        lect = await c.post(
            "/admin/users",
            headers=ADMIN,
            json={"email": "lect.one@uni.edu", "displayName": "Lect One", "role": "lecturer", "password": "secret12"},
        )
        lect = lect.json()

        dup = await c.post(
            "/admin/users",
            headers=ADMIN,
            json={"email": "lect.one@uni.edu", "displayName": "Again", "role": "lecturer", "password": "secret12"},
        )
        assert dup.status_code == 409

        # A module's moderator must be an active moderator; assigning one notifies both people.
        bad = await c.post(
            "/courses", headers=ADMIN, json={"code": "IT9001", "title": "Networks", "ownerUid": lect["uid"], "moderatorUid": lect["uid"]}
        )
        assert bad.status_code == 422
        ok = await c.post(
            "/courses", headers=ADMIN, json={"code": "IT9001", "title": "Networks", "ownerUid": lect["uid"], "moderatorUid": mod["uid"]}
        )
        assert ok.status_code == 201 and ok.json()["moderatorUid"] == mod["uid"]
        assert any(n["type"] == "moderator_assigned" for n in await db.query("notifications", filters=[("recipientUid", "==", mod["uid"])]))
        assert any(n["type"] == "moderator_assigned" for n in await db.query("notifications", filters=[("recipientUid", "==", lect["uid"])]))

        # Demoting the moderator clears them from the module.
        await c.patch(f"/admin/users/{mod['uid']}", headers=ADMIN, json={"role": "admin"})
        assert (await db.get("courses", "IT9001"))["moderatorUid"] is None
        await db.delete("courses", "IT9001")


@pytest.mark.asyncio
async def test_one_lecturer_two_modules_two_moderators():
    """Moderation follows the module: each of a lecturer's modules can have its own moderator."""
    async with client() as c:
        mod2 = (
            await c.post(
                "/admin/users",
                headers=ADMIN,
                json={"email": "mod.two@uni.edu", "displayName": "Mod Two", "role": "moderator", "password": "secret12"},
            )
        ).json()
        made = await c.post(
            "/courses",
            headers=ADMIN,
            json={"code": "IT9002", "title": "Security", "ownerUid": "demo-lecturer-uid", "moderatorUid": mod2["uid"]},
        )
        assert made.status_code == 201, made.text

        contacts = (await c.get("/me/contacts", headers=LECTURER)).json()
        by_code = {m["code"]: m["moderator"]["uid"] for m in contacts["modules"]}
        assert by_code["CS2040"] == "demo-moderator-uid" and by_code["IT9002"] == mod2["uid"]

        await db.set("assessments", "asm-it9002", {**(await db.get("assessments", "asm-demo")), "id": "asm-it9002", "courseId": "IT9002"})
        sub = await c.post("/assessments/asm-it9002/submit", headers=LECTURER)
        assert sub.status_code == 200, sub.text
        assert sub.json()["moderatorUid"] == mod2["uid"]
        # The CS2040 moderator does not see the IT9002 paper.
        assert (await c.get("/assessments/asm-it9002", headers=MODERATOR)).status_code == 404

        # Reassigning the module's moderator is an admin-only PATCH.
        assert (await c.patch("/courses/IT9002", headers=LECTURER, json={"moderatorUid": ""})).status_code == 403
        cleared = await c.patch("/courses/IT9002", headers=ADMIN, json={"moderatorUid": ""})
        assert cleared.status_code == 200 and cleared.json()["moderatorUid"] is None
        await db.delete("assessments", "asm-it9002")
        await db.delete("courses", "IT9002")


@pytest.mark.asyncio
async def test_admin_cannot_lock_themselves_out():
    async with client() as c:
        resp = await c.patch("/admin/users/demo-admin-uid", headers=ADMIN, json={"disabled": True})
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_lecturer_sees_assigned_moderator_contact():
    async with client() as c:
        lect = (await c.get("/me/contacts", headers=LECTURER)).json()
        cs2040 = next(m for m in lect["modules"] if m["code"] == "CS2040")
        assert cs2040["moderator"]["email"] == "moderator@demo"
        mod = (await c.get("/me/contacts", headers=MODERATOR)).json()
        assert any(l["email"] == "lecturer@demo" for l in mod["lecturers"])
        assert any(m["code"] == "CS2040" and m["owner"]["email"] == "lecturer@demo" for m in mod["modules"])
        module = (await c.get("/courses/CS2040/contacts", headers=LECTURER)).json()
        assert module["moderator"]["email"] == "moderator@demo"


@pytest.mark.asyncio
async def test_submit_notify_review_loop():
    async with client() as c:
        # Before submission the moderator cannot see or decide on the paper.
        assert (await c.get("/assessments/asm-demo", headers=MODERATOR)).status_code == 404
        early = await c.post("/assessments/asm-demo/decision", headers=MODERATOR, json={"decision": "approved"})
        assert early.status_code == 404

        before = len(await _notes(c, MODERATOR))
        sub = await c.post("/assessments/asm-demo/submit", headers=LECTURER)
        assert sub.status_code == 200, sub.text
        assert sub.json()["moderatorUid"] == "demo-moderator-uid"

        notes = await _notes(c, MODERATOR)
        assert len(notes) == before + 1
        assert notes[0]["type"] == "submitted_for_moderation" and notes[0]["assessmentId"] == "asm-demo"

        # Moderator now sees it in their list and requests changes.
        listed = (await c.get("/assessments", headers=MODERATOR)).json()
        assert [a["id"] for a in listed] == ["asm-demo"]
        rc = await c.post(
            "/assessments/asm-demo/decision",
            headers=MODERATOR,
            json={"decision": "changes_requested", "comment": "Rebalance Q4."},
        )
        assert rc.status_code == 200, rc.text
        # Regression: an assessment in changes_requested must still load.
        got = await c.get("/assessments/asm-demo", headers=LECTURER)
        assert got.status_code == 200 and got.json()["status"] == "changes_requested"
        lect_notes = await _notes(c, LECTURER)
        assert lect_notes[0]["type"] == "moderation_changes_requested"
        assert "Rebalance Q4." in lect_notes[0]["message"]

        # A second decision without a resubmission is refused.
        again = await c.post("/assessments/asm-demo/decision", headers=MODERATOR, json={"decision": "approved"})
        assert again.status_code == 409

        # Resubmit -> approve -> lecturer notified.
        assert (await c.post("/assessments/asm-demo/submit", headers=LECTURER)).status_code == 200
        ok = await c.post("/assessments/asm-demo/decision", headers=MODERATOR, json={"decision": "approved"})
        assert ok.status_code == 200
        assert (await _notes(c, LECTURER))[0]["type"] == "moderation_approved"

        # Mark-all-read clears the unread count.
        await c.post("/notifications/read-all", headers=LECTURER)
        assert all(n["read"] for n in await _notes(c, LECTURER))


@pytest.mark.asyncio
async def test_submit_requires_assigned_moderator():
    await db.update("courses", "CS2040", {"moderatorUid": None})
    async with client() as c:
        resp = await c.post("/assessments/asm-demo/submit", headers=LECTURER)
        assert resp.status_code == 409
        assert "CS2040" in resp.json()["detail"] and "administrator" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_demo_records_are_not_provisioned_and_labels_are_not_names():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        users = {u["uid"]: u for u in (await c.get("/admin/users", headers=ADMIN)).json()}
    lect = users["demo-lecturer-uid"]
    assert lect["authProvisioned"] is False
    assert (lect["title"], lect["firstName"], lect["lastName"]) == ("Dr.", "Samantha", "Chen")
