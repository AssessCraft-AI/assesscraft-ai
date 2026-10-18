import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from app.models import (
    Course,
    CourseCreate,
    CourseOutcomesUpdate,
    CourseUpdate,
    User,
    current_time_iso,
    normalize_roles,
    roles_of,
)
from app.services import identity
from app.services.firestore import db
from app.services.audit import log_audit
from app.services.notifications import notify
from app.tools.events import log_event
from app.auth import get_current_user, require_role
from app.api.me import ModuleContacts, module_contacts

router = APIRouter(prefix="/courses", tags=["courses"])
logger = logging.getLogger("assesscraft.courses")


@router.get("", response_model=List[Course])
async def list_courses(current_user: User = Depends(get_current_user)):
    docs = await db.query("courses")
    return [Course(**d) for d in docs if can_access_course(d, current_user)]


def can_access_course(course: dict, user: User) -> bool:
    """Lecturers and moderators only see the modules assigned to them; admins see all."""
    return user.has_role("admin", "system") or user.uid in (course.get("ownerUid"), course.get("moderatorUid"))


async def get_accessible_course(course_id: str, user: User) -> dict:
    course = await db.get("courses", course_id)
    if not course or not can_access_course(course, user):
        # 404 rather than 403 so other modules' existence is not disclosed.
        raise HTTPException(status_code=404, detail="Module not found")
    return course


@router.post("", response_model=Course, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    current_user: User = Depends(require_role(["admin"])),
):
    course_id = payload.code.strip().upper()
    if not course_id or not payload.title.strip():
        raise HTTPException(status_code=422, detail="Module code and title are required")
    existing = await db.get("courses", course_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Module {course_id} already exists")

    owner_uid = await _require_lecturer(payload.ownerUid)
    moderator_uid = await _require_moderator(payload.moderatorUid)
    _require_distinct(owner_uid, moderator_uid)
    await _grant_moderator_role(moderator_uid, current_user)

    course = Course(
        id=course_id,
        code=course_id,
        title=payload.title.strip(),
        ownerUid=owner_uid,
        moderatorUid=moderator_uid,
        clos=payload.clos or [],
        topics=payload.topics or [],
        confirmed=False,
    )
    await db.set("courses", course.id, course.model_dump())
    await log_audit(
        actor_uid=current_user.uid,
        action="create_course",
        entity="courses",
        entity_id=course.id,
        after=course.model_dump(),
    )
    await log_event(
        event_type="course_created",
        user_role=current_user.role,
        meta={"course_id": course.id, "code": course.code},
    )
    await _notify_assignments(course.model_dump(), owner_changed=bool(owner_uid), moderator_changed=bool(moderator_uid))
    return course


async def _require_lecturer(uid: Optional[str]) -> str:
    """Validates a module owner; returns "" (unassigned) for an empty uid."""
    if not uid:
        return ""
    owner = await db.get("users", uid)
    if not owner or "lecturer" not in roles_of(owner) or owner.get("disabled"):
        raise HTTPException(status_code=422, detail="The module's lecturer must be an active lecturer")
    return uid


async def _require_moderator(uid: Optional[str]) -> Optional[str]:
    """Validates a module moderator: an active moderator, or a lecturer who can also moderate. None when unassigned."""
    if not uid:
        return None
    mod = await db.get("users", uid)
    if not mod or mod.get("disabled") or not {"moderator", "lecturer"} & set(roles_of(mod)):
        raise HTTPException(status_code=422, detail="The module's moderator must be an active moderator or lecturer")
    return uid


async def _grant_moderator_role(uid: Optional[str], actor: User) -> None:
    """A lecturer picked as a module's moderator also gets the moderator role, so they can review and sign off its papers."""
    doc = await db.get("users", uid) if uid else None
    if not doc or "moderator" in roles_of(doc):
        return
    roles = normalize_roles([*roles_of(doc), "moderator"])
    if not (uid.startswith("demo-") or uid.startswith("local-")):
        try:
            await identity.update_account(uid, roles=roles)
        except identity.IdentityUnavailable as e:
            # The users/{uid} record is what sign-in reads first, so the claim can catch up later.
            logger.warning("Could not update role claims for %s: %s", uid, e)
    before = dict(doc)
    doc.update(roles=roles, role=roles[0], updatedAt=current_time_iso())
    await db.set("users", uid, doc)
    await log_audit(
        actor_uid=actor.uid,
        action="grant_moderator_role",
        entity="users",
        entity_id=uid,
        before={"roles": roles_of(before)},
        after={"roles": roles},
    )


def require_course_owner(course: dict, user: User) -> None:
    """Module content (outcomes, documents, papers) is changed only by the module's lecturer."""
    if not course.get("ownerUid") or course["ownerUid"] != user.uid:
        raise HTTPException(status_code=403, detail="Only the module's lecturer can change this module")


def _require_distinct(owner_uid: Optional[str], moderator_uid: Optional[str]) -> None:
    """A user with both roles may moderate other modules, never one they own."""
    if owner_uid and moderator_uid and owner_uid == moderator_uid:
        raise HTTPException(status_code=422, detail="A module's lecturer cannot also be its moderator")


async def _notify_assignments(course: dict, *, owner_changed: bool, moderator_changed: bool) -> None:
    label = f"{course['code']} · {course['title']}"
    owner = await db.get("users", course["ownerUid"]) if course.get("ownerUid") else None
    mod = await db.get("users", course["moderatorUid"]) if course.get("moderatorUid") else None
    if owner_changed and owner:
        await notify(owner["uid"], "module_assigned", "Module assigned", f"You are now the lecturer for {label}.")
    if moderator_changed and mod:
        await notify(
            mod["uid"],
            "moderator_assigned",
            "Module to moderate",
            f"You will moderate papers for {label}"
            + (f" from {owner.get('displayName')} ({owner.get('email')})." if owner else "."),
        )
    # The owner learns who moderates the module whenever either side of the pair changes.
    if owner and mod and (owner_changed or moderator_changed):
        await notify(
            owner["uid"],
            "moderator_assigned",
            "Moderator assigned",
            f"{mod.get('displayName')} ({mod.get('email')}) will moderate your {course['code']} papers.",
        )


@router.patch("/{course_id}", response_model=Course)
async def update_course(
    course_id: str,
    payload: CourseUpdate,
    current_user: User = Depends(require_role(["admin"])),
):
    doc = await db.get("courses", course_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Module not found")

    before = dict(doc)
    if payload.title is not None:
        if not payload.title.strip():
            raise HTTPException(status_code=422, detail="Module title cannot be empty")
        doc["title"] = payload.title.strip()
    owner_uid = await _require_lecturer(payload.ownerUid) if payload.ownerUid is not None else doc.get("ownerUid")
    moderator_uid = (
        await _require_moderator(payload.moderatorUid) if payload.moderatorUid is not None else doc.get("moderatorUid")
    )
    _require_distinct(owner_uid, moderator_uid)
    if payload.ownerUid is not None:
        doc["ownerUid"] = owner_uid
    if payload.moderatorUid is not None:
        await _grant_moderator_role(moderator_uid, current_user)
        doc["moderatorUid"] = moderator_uid
    doc["updatedAt"] = current_time_iso()

    saved = await db.set("courses", course_id, doc)
    await log_audit(
        actor_uid=current_user.uid,
        action="admin_update_course",
        entity="courses",
        entity_id=course_id,
        before=before,
        after=saved,
    )
    await _notify_assignments(
        saved,
        owner_changed=bool(saved.get("ownerUid")) and saved.get("ownerUid") != before.get("ownerUid"),
        moderator_changed=bool(saved.get("moderatorUid")) and saved.get("moderatorUid") != before.get("moderatorUid"),
    )
    return Course(**saved)


@router.get("/{course_id}/contacts", response_model=ModuleContacts)
async def course_contacts(course_id: str, current_user: User = Depends(get_current_user)):
    """The module's owning lecturer and moderator, as shown on the paper's moderation panel."""
    return await module_contacts(await get_accessible_course(course_id, current_user))


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course_id: str, current_user: User = Depends(require_role(["admin"]))):
    doc = await db.get("courses", course_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Module not found")
    assessments = await db.query("assessments", filters=[("courseId", "==", course_id)])
    if assessments:
        raise HTTPException(
            status_code=409,
            detail=f"{course_id} has {len(assessments)} assessment(s); delete or move them before deleting the module",
        )
    await db.delete("courses", course_id)
    await log_audit(
        actor_uid=current_user.uid,
        action="admin_delete_course",
        entity="courses",
        entity_id=course_id,
        before=doc,
    )


@router.get("/{course_id}", response_model=Course)
async def get_course(course_id: str, current_user: User = Depends(get_current_user)):
    doc = await db.get("courses", course_id)
    if not doc:
        # Check by code match
        by_code = await db.query("courses", filters=[("code", "==", course_id.upper())])
        doc = by_code[0] if by_code else None
    if not doc or not can_access_course(doc, current_user):
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found")
    return Course(**doc)


@router.put("/{course_id}/outcomes", response_model=Course)
async def update_course_outcomes(
    course_id: str,
    payload: CourseOutcomesUpdate,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    course_data = await db.get("courses", course_id)
    if not course_data:
        raise HTTPException(status_code=404, detail="Course not found")
    require_course_owner(course_data, current_user)

    before = dict(course_data)
    course_data["clos"] = [c.model_dump() for c in payload.clos]
    course_data["topics"] = [t.model_dump() for t in payload.topics]
    course_data["confirmed"] = payload.confirmed

    updated = await db.set("courses", course_id, course_data)
    await log_audit(
        actor_uid=current_user.uid,
        action="update_outcomes",
        entity="courses",
        entity_id=course_id,
        before=before,
        after=updated,
    )
    await log_event(
        event_type="outcomes_confirmed",
        user_role=current_user.role,
        meta={"course_id": course_id, "clos_count": len(payload.clos)},
    )
    return Course(**updated)
