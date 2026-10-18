from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user
from app.models import User, UserSummary, roles_of
from app.services.firestore import db

router = APIRouter(tags=["auth"])


class ModuleContacts(BaseModel):
    """One module with its owning lecturer and its moderator."""
    courseId: str
    code: str
    title: str
    owner: Optional[UserSummary] = None
    moderator: Optional[UserSummary] = None


class MyContacts(BaseModel):
    # The modules the user owns (each with its moderator) and moderates (each with its owning lecturer).
    modules: List[ModuleContacts] = []
    # Moderators: the distinct lecturers whose papers they review.
    lecturers: List[UserSummary] = []


def _summary(doc: dict) -> UserSummary:
    roles = roles_of(doc) or ["lecturer"]
    return UserSummary(
        uid=doc["uid"],
        email=doc.get("email", ""),
        displayName=doc.get("displayName", ""),
        role=roles[0],
        roles=roles,
        institution=doc.get("institution"),
    )


async def _active(uid: Optional[str], role: str) -> Optional[UserSummary]:
    doc = await db.get("users", uid) if uid else None
    if not doc or doc.get("disabled") or role not in roles_of(doc):
        return None
    return _summary(doc)


async def module_contacts(course: dict) -> ModuleContacts:
    return ModuleContacts(
        courseId=course["id"],
        code=course.get("code", course["id"]),
        title=course.get("title", ""),
        owner=await _active(course.get("ownerUid"), "lecturer"),
        moderator=await _active(course.get("moderatorUid"), "moderator"),
    )


async def module_moderator_uid(course_id: str) -> Optional[str]:
    """The active moderator assigned to a module, or None."""
    course = await db.get("courses", course_id) if course_id else None
    if not course:
        return None
    mod = await _active(course.get("moderatorUid"), "moderator")
    return mod.uid if mod else None


@router.get("/me", response_model=User)
async def me(current_user: User = Depends(get_current_user)):
    """The authenticated user with the server-resolved role (the frontend never decides roles)."""
    return current_user


@router.get("/me/contacts", response_model=MyContacts)
async def my_contacts(current_user: User = Depends(get_current_user)):
    contacts = MyContacts()
    courses = {}
    if current_user.has_role("lecturer"):
        for c in await db.query("courses", filters=[("ownerUid", "==", current_user.uid)]):
            courses[c["id"]] = c
    moderated = []
    if current_user.has_role("moderator"):
        moderated = await db.query("courses", filters=[("moderatorUid", "==", current_user.uid)])
        for c in moderated:
            courses[c["id"]] = c
    contacts.modules = sorted([await module_contacts(c) for c in courses.values()], key=lambda m: m.code)
    moderated_ids = {c["id"] for c in moderated}
    seen = {}
    for m in contacts.modules:
        if m.courseId in moderated_ids and m.owner:
            seen.setdefault(m.owner.uid, m.owner)
    contacts.lecturers = list(seen.values())
    return contacts
