"""One user holding several roles: a lecturer who also moderates other lecturers' modules."""
import itertools

import pytest
from httpx import AsyncClient, ASGITransport

from app import auth as auth_module
from app.main import app
from app.services import identity
from app.services.firestore import db
from seed.load_seed import seed_database

ADMIN = {"X-Demo-Role": "admin"}
LECTURER = {"X-Demo-Role": "lecturer"}

_uids = itertools.count(1)


@pytest.fixture(autouse=True)
async def setup(monkeypatch):
    await seed_database()
    claims_set = {}

    async def fake_create_account(email, password, display_name, roles):
        claims_set["created"] = roles
        return f"multi-uid-{next(_uids)}"

    async def fake_update_account(uid, **changes):
        return None

    def fake_verify(token, *a, **k):
        # "tok-<uid>" signs in as that uid; roles then come from the users/{uid} record.
        if not token.startswith("tok-"):
            raise ValueError("bad token")
        return {"uid": token[4:], "email": f"{token[4:]}@uni.edu"}

    monkeypatch.setattr(identity, "create_account", fake_create_account)
    monkeypatch.setattr(identity, "update_account", fake_update_account)
    monkeypatch.setattr(auth_module.firebase_auth, "verify_id_token", fake_verify)
    return claims_set


def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def as_user(uid):
    return {"Authorization": f"Bearer tok-{uid}"}


_emails = itertools.count(1)


async def _create_dual(c):
    # Seeding does not clear users, so each test gets its own address.
    resp = await c.post(
        "/admin/users",
        headers=ADMIN,
        json={"email": f"dual{next(_emails)}@uni.edu", "displayName": "Dual Role", "roles": ["moderator", "lecturer"], "password": "secret12"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_admin_creates_user_with_several_roles(setup):
    async with client() as c:
        dual = await _create_dual(c)
        assert dual["roles"] == ["lecturer", "moderator"] and dual["role"] == "lecturer"
        assert setup["created"] == ["lecturer", "moderator"]

        me = (await c.get("/me", headers=as_user(dual["uid"]))).json()
        assert me["roles"] == ["lecturer", "moderator"]

        empty = await c.patch(f"/admin/users/{dual['uid']}", headers=ADMIN, json={"roles": []})
        assert empty.status_code == 422


@pytest.mark.asyncio
async def test_legacy_single_role_records_still_work():
    await db.set("users", "legacy-uid", {"uid": "legacy-uid", "email": "legacy@uni.edu", "displayName": "Legacy", "role": "moderator"})
    async with client() as c:
        me = (await c.get("/me", headers=as_user("legacy-uid"))).json()
        assert me["role"] == "moderator" and me["roles"] == ["moderator"]


@pytest.mark.asyncio
async def test_dual_role_user_moderates_others_but_never_their_own_module():
    async with client() as c:
        dual = await _create_dual(c)
        uid = dual["uid"]

        # Moderates the demo lecturer's CS2040; owns IT9100, moderated by the demo moderator.
        assigned = await c.patch("/courses/CS2040", headers=ADMIN, json={"moderatorUid": uid})
        assert assigned.status_code == 200, assigned.text
        owned = await c.post(
            "/courses", headers=ADMIN, json={"code": "IT9100", "title": "Cloud", "ownerUid": uid, "moderatorUid": "demo-moderator-uid"}
        )
        assert owned.status_code == 201, owned.text

        # The owner of a module cannot also be its moderator.
        clash = await c.patch("/courses/IT9100", headers=ADMIN, json={"moderatorUid": uid})
        assert clash.status_code == 422

        contacts = (await c.get("/me/contacts", headers=as_user(uid))).json()
        assert {m["code"] for m in contacts["modules"]} >= {"CS2040", "IT9100"}
        assert [l["uid"] for l in contacts["lecturers"]] == ["demo-lecturer-uid"]

        # The demo lecturer's paper goes to the dual-role user, who can read and approve it.
        assert (await c.get("/assessments/asm-demo", headers=as_user(uid))).status_code == 404
        sub = await c.post("/assessments/asm-demo/submit", headers=LECTURER)
        assert sub.status_code == 200 and sub.json()["moderatorUid"] == uid
        assert (await c.get("/assessments/asm-demo", headers=as_user(uid))).status_code == 200
        ok = await c.post(
            "/assessments/asm-demo/decision", headers=as_user(uid), json={"decision": "approved", "comment": "Looks good."}
        )
        assert ok.status_code == 200, ok.text
        assert ok.json()["humanComments"][-1]["role"] == "moderator"

        # Even if a paper they wrote were routed to them, they cannot decide on it.
        await db.set(
            "assessments",
            "asm-own",
            {
                **(await db.get("assessments", "asm-demo")),
                "id": "asm-own",
                "courseId": "IT9100",
                "createdBy": dual["email"],
                "createdByUid": uid,
                "status": "in_moderation",
                "moderatorUid": uid,
            },
        )
        own = await c.post("/assessments/asm-own/decision", headers=as_user(uid), json={"decision": "approved"})
        assert own.status_code == 403

        # Dropping the moderator role clears them from the module they moderated.
        dropped = await c.patch(f"/admin/users/{uid}", headers=ADMIN, json={"roles": ["lecturer"]})
        assert dropped.status_code == 200 and dropped.json()["roles"] == ["lecturer"]
        assert (await db.get("courses", "CS2040"))["moderatorUid"] is None

        await db.delete("assessments", "asm-own")
        await db.delete("courses", "IT9100")


@pytest.mark.asyncio
async def test_admin_can_add_roles_to_themselves_but_not_drop_admin():
    async with client() as c:
        drop = await c.patch("/admin/users/demo-admin-uid", headers=ADMIN, json={"roles": ["lecturer"]})
        assert drop.status_code == 400
        add = await c.patch("/admin/users/demo-admin-uid", headers=ADMIN, json={"roles": ["admin", "lecturer"]})
        assert add.status_code == 200, add.text
        assert add.json()["roles"] == ["admin", "lecturer"]


@pytest.mark.asyncio
async def test_admin_sets_title_separately_from_name():
    async with client() as c:
        made = await c.post(
            "/admin/users",
            headers=ADMIN,
            json={"email": "titled@uni.edu", "displayName": "Amali Perera", "title": "Dr.", "role": "moderator", "password": "secret12"},
        )
        assert made.status_code == 201, made.text
        user = made.json()
        assert user["title"] == "Dr." and user["displayName"] == "Dr. Amali Perera"

        # Changing only the title keeps the name; "" removes it.
        miss = (await c.patch(f"/admin/users/{user['uid']}", headers=ADMIN, json={"title": "Miss"})).json()
        assert miss["displayName"] == "Miss Amali Perera"
        plain = (await c.patch(f"/admin/users/{user['uid']}", headers=ADMIN, json={"title": ""})).json()
        assert plain["displayName"] == "Amali Perera" and plain["title"] is None

        # Older records with the title typed into the name still report it.
        await db.set("users", "old-uid", {"uid": "old-uid", "email": "old@uni.edu", "displayName": "Mr. Praveen Sampath", "role": "lecturer"})
        listed = {u["uid"]: u for u in (await c.get("/admin/users", headers=ADMIN)).json()}
        assert listed["old-uid"]["title"] == "Mr."
        await db.delete("users", "old-uid")


@pytest.mark.asyncio
async def test_admin_sets_first_middle_and_last_name():
    async with client() as c:
        made = await c.post(
            "/admin/users",
            headers=ADMIN,
            json={
                "email": "parts@uni.edu",
                "title": "Ms.",
                "firstName": "Amali",
                "middleName": "Nadeesha",
                "lastName": "Perera",
                "role": "lecturer",
                "password": "secret12",
            },
        )
        assert made.status_code == 201, made.text
        user = made.json()
        assert user["displayName"] == "Ms. Amali Nadeesha Perera"
        assert (user["firstName"], user["middleName"], user["lastName"]) == ("Amali", "Nadeesha", "Perera")

        # Clearing the middle name keeps the rest.
        edited = (await c.patch(f"/admin/users/{user['uid']}", headers=ADMIN, json={"middleName": ""})).json()
        assert edited["displayName"] == "Ms. Amali Perera" and edited["middleName"] == ""

        missing = await c.patch(f"/admin/users/{user['uid']}", headers=ADMIN, json={"firstName": " "})
        assert missing.status_code == 422

        # Older records are split into parts for the edit form.
        await db.set("users", "old-uid", {"uid": "old-uid", "email": "old@uni.edu", "displayName": "Dr. Kamal Nimal Silva", "role": "lecturer"})
        listed = {u["uid"]: u for u in (await c.get("/admin/users", headers=ADMIN)).json()}
        old = listed["old-uid"]
        assert (old["title"], old["firstName"], old["middleName"], old["lastName"]) == ("Dr.", "Kamal", "Nimal", "Silva")
        await db.delete("users", "old-uid")


@pytest.mark.asyncio
async def test_examiner_picked_as_moderator_gains_the_role():
    async with client() as c:
        made = await c.post(
            "/admin/users",
            headers=ADMIN,
            json={"email": "examiner.only@uni.edu", "firstName": "Exam", "lastName": "Only", "role": "lecturer", "password": "secret12"},
        )
        uid = made.json()["uid"]
        assert made.json()["roles"] == ["lecturer"]

        assigned = await c.patch("/courses/CS2040", headers=ADMIN, json={"moderatorUid": uid})
        assert assigned.status_code == 200, assigned.text
        assert (await db.get("users", uid))["roles"] == ["lecturer", "moderator"]

        # They now receive and can sign off the demo examiner's paper.
        assert (await c.post("/assessments/asm-demo/submit", headers=LECTURER)).json()["moderatorUid"] == uid
        ok = await c.post("/assessments/asm-demo/decision", headers=as_user(uid), json={"decision": "approved"})
        assert ok.status_code == 200, ok.text

        # An admin-only user still cannot moderate.
        admin = await c.patch("/courses/CS2040", headers=ADMIN, json={"moderatorUid": "demo-admin-uid"})
        assert admin.status_code == 422
