from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.models import (
    AdminUserCreate,
    AdminUserUpdate,
    User,
    current_time_iso,
    generate_id,
    join_name,
    name_parts,
    normalize_roles,
    roles_of,
    split_name,
    split_title,
    with_title,
)
from app.services import identity
from app.services.audit import log_audit
from app.services.firestore import db
from app.auth import require_role

router = APIRouter(prefix="/admin", tags=["admin"])

require_admin = require_role(["admin"])


class AdminUserView(User):
    # False for a record created while Firebase Admin was unreachable (demo mode): it cannot sign in.
    authProvisioned: bool = True


def _is_firebase_uid(uid: str) -> bool:
    return not (uid.startswith("demo-") or uid.startswith("local-"))


def _view(doc: dict) -> AdminUserView:
    view = AdminUserView(**{k: v for k, v in doc.items() if k != "id"})
    view.authProvisioned = _is_firebase_uid(view.uid)
    # Older records keep the title and every name in displayName ("Dr. Amali Perera").
    view.title, view.firstName, view.middleName, view.lastName = name_parts(doc)
    return view


async def _get_user_or_404(uid: str) -> dict:
    doc = await db.get("users", uid)
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return doc


async def _sync_account(uid: str, **changes) -> None:
    if not _is_firebase_uid(uid):
        return
    try:
        await identity.update_account(uid, **changes)
    except identity.IdentityUnavailable as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Firebase Admin is not configured on the server, so the sign-in account was not changed ({e})",
        )


@router.get("/users", response_model=List[AdminUserView])
async def list_users(current_user: User = Depends(require_admin)):
    docs = await db.query("users")
    users = [_view(d) for d in docs if d.get("uid")]
    return sorted(users, key=lambda u: (u.role, u.displayName.lower()))


@router.post("/users", response_model=AdminUserView, status_code=status.HTTP_201_CREATED)
async def create_user(payload: AdminUserCreate, current_user: User = Depends(require_admin)):
    email = payload.email.strip().lower()
    existing = await db.query("users", filters=[("email", "==", email)])
    if existing:
        raise HTTPException(status_code=409, detail=f"A user with email {email} already exists")

    roles = payload.resolved_roles()
    first, middle, last = payload.resolved_name()
    if not first:
        raise HTTPException(status_code=422, detail="First name is required")
    display_name = with_title(payload.title, join_name(first, middle, last))
    provisioned = True
    try:
        uid = await identity.create_account(email, payload.password, display_name, roles)
    except identity.EmailAlreadyExists:
        raise HTTPException(status_code=409, detail=f"A Firebase account for {email} already exists")
    except identity.IdentityUnavailable as e:
        if not settings.ENABLE_DEMO_AUTH:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Firebase Admin is not configured on the server, so the account could not be created ({e})",
            )
        # Demo/local mode: keep a record so the assignment flow can be exercised, but it cannot sign in.
        uid = f"local-{generate_id()[:12]}"
        provisioned = False

    record = AdminUserView(
        uid=uid,
        email=email,
        displayName=display_name,
        title=payload.title,
        firstName=first,
        middleName=middle,
        lastName=last,
        roles=roles,
        institution=payload.institution or "AssessCraft University",
        authProvisioned=provisioned,
    )
    await db.set("users", uid, record.model_dump())
    await log_audit(
        actor_uid=current_user.uid,
        action="admin_create_user",
        entity="users",
        entity_id=uid,
        after={"email": email, "roles": record.roles},
    )
    return record


@router.patch("/users/{uid}", response_model=AdminUserView)
async def update_user(uid: str, payload: AdminUserUpdate, current_user: User = Depends(require_admin)):
    doc = await _get_user_or_404(uid)
    old_roles = roles_of(doc)
    new_roles = normalize_roles(payload.roles) if payload.roles is not None else ([payload.role] if payload.role else None)
    if new_roles is not None and not new_roles:
        raise HTTPException(status_code=422, detail="A user needs at least one role")
    if uid == current_user.uid and (payload.disabled or (new_roles is not None and "admin" not in new_roles)):
        raise HTTPException(status_code=400, detail="You cannot disable or demote your own admin account")

    if payload.password and not _is_firebase_uid(uid):
        raise HTTPException(status_code=422, detail="This is a local record with no sign-in account, so it has no password")

    before = dict(doc)
    roles_changed = new_roles is not None and new_roles != old_roles
    display_name = None
    name_fields = (payload.title, payload.firstName, payload.middleName, payload.lastName, payload.displayName)
    if any(f is not None for f in name_fields):
        title, first, middle, last = name_parts(doc)
        if payload.title is not None:
            title = payload.title or None
        if payload.displayName is not None:
            first, middle, last = split_name(split_title(payload.displayName)[1])
        first = payload.firstName.strip() if payload.firstName is not None else first
        middle = payload.middleName.strip() if payload.middleName is not None else middle
        last = payload.lastName.strip() if payload.lastName is not None else last
        if not first:
            raise HTTPException(status_code=422, detail="First name is required")
        display_name = with_title(title, join_name(first, middle, last))
    await _sync_account(
        uid,
        roles=new_roles if roles_changed else None,
        display_name=display_name,
        disabled=payload.disabled,
        password=payload.password,
    )

    if display_name is not None:
        doc.update(displayName=display_name, title=title, firstName=first, middleName=middle, lastName=last)
    if payload.institution is not None:
        doc["institution"] = payload.institution
    if payload.disabled is not None:
        doc["disabled"] = payload.disabled
    if roles_changed:
        doc["roles"] = new_roles
        doc["role"] = new_roles[0]
        if "moderator" in old_roles and "moderator" not in new_roles:
            await _clear_module_moderator(uid)
    doc["updatedAt"] = current_time_iso()

    saved = await db.set("users", uid, doc)
    await log_audit(
        actor_uid=current_user.uid,
        action="admin_update_user",
        entity="users",
        entity_id=uid,
        before=before,
        # Never write the password into the audit trail.
        after={**saved, "passwordReset": bool(payload.password)},
    )
    return _view(saved)


async def _clear_module_moderator(moderator_uid: str) -> None:
    """A user who loses the moderator role stops moderating; their modules need a new moderator."""
    for course in await db.query("courses", filters=[("moderatorUid", "==", moderator_uid)]):
        course["moderatorUid"] = None
        course["updatedAt"] = current_time_iso()
        await db.set("courses", course["id"], course)
