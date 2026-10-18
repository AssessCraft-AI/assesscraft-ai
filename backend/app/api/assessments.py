import asyncio
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from app.models import Assessment, AssessmentCreate, User, current_time_iso, generate_id
from app.services.firestore import db
from app.services.audit import log_audit
from app.services.notifications import notify
from app.services.traces import tracker
from app.tools.events import log_event
from app.auth import get_current_user, require_role
from app.api.me import module_moderator_uid
from app.api.courses import require_course_owner

router = APIRouter(prefix="/assessments", tags=["assessments"])

# Statuses from which a lecturer may (re)submit a finished paper for moderation.
SUBMITTABLE_STATUSES = ("assembled", "changes_requested")
# Statuses in which the paper's content is frozen: under review, or signed off.
LOCKED_STATUSES = ("in_moderation", "approved")


def is_owner(doc: dict, user: User) -> bool:
    if doc.get("createdByUid"):
        return doc["createdByUid"] == user.uid
    return doc.get("createdBy") == user.email


def is_paper_moderator(doc: dict, user: User) -> bool:
    return user.has_role("moderator") and bool(doc.get("moderatorUid")) and doc["moderatorUid"] == user.uid


def can_view(doc: dict, user: User) -> bool:
    """Users see the papers they wrote and the papers submitted to them for moderation; admins see everything."""
    if user.has_role("admin", "system"):
        return True
    return is_paper_moderator(doc, user) or is_owner(doc, user)


def role_on_paper(doc: dict, user: User) -> str:
    """The capacity a multi-role user acts in on this paper (shown on their comments)."""
    if is_paper_moderator(doc, user):
        return "moderator"
    if is_owner(doc, user) and user.has_role("lecturer"):
        return "lecturer"
    return user.role


async def get_visible_assessment(assessment_id: str, user: User) -> dict:
    doc = await db.get("assessments", assessment_id)
    if not doc or not can_view(doc, user):
        # 404 rather than 403 so other users' paper ids are not disclosed.
        raise HTTPException(status_code=404, detail="Assessment not found")
    return doc


async def get_editable_assessment(assessment_id: str, user: User) -> dict:
    """Only the paper's lecturer may change it, and only before it goes to moderation or after changes are requested."""
    doc = await get_visible_assessment(assessment_id, user)
    if not is_owner(doc, user):
        raise HTTPException(status_code=403, detail="Only the lecturer who created this paper can change it")
    if doc.get("status") in LOCKED_STATUSES:
        raise HTTPException(status_code=409, detail="This paper is in moderation or approved, so it cannot be changed")
    return doc


# Item fields the assembled versions were solved against (marks, CLO/topic/Bloom parity, rejection).
ASSEMBLY_FIELDS = ("status", "marks", "cloId", "topicId", "bloom")


async def reopen_assembly(doc: dict, item_id: str) -> None:
    """An assembled paper whose questions changed must be assembled again before it can be submitted."""
    if doc.get("status") not in SUBMITTABLE_STATUSES:
        return
    versions = await db.query("versions", filters=[("assessmentId", "==", doc["id"])])
    if any(item_id in v.get("itemIds", []) for v in versions):
        await db.update("assessments", doc["id"], {"status": "reviewed"})


@router.get("", response_model=List[Assessment])
async def list_assessments(
    course_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    filters = [("courseId", "==", course_id)] if course_id else None
    docs = await db.query("assessments", filters=filters)
    results = []
    for d in docs:
        if not can_view(d, current_user):
            continue
        try:
            results.append(Assessment(**d))
        except Exception as e:
            print(f"[list_assessments] Skipping malformed assessment doc {d.get('id')}: {e}")
    return results


@router.post("", response_model=Assessment, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: AssessmentCreate,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    course = await db.get("courses", payload.courseId)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    require_course_owner(course, current_user)
    if not course.get("clos") or not course.get("topics"):
        raise HTTPException(
            status_code=400,
            detail="This course has no learning outcomes yet. Upload materials and extract outcomes first.",
        )
    aid = f"asm-{generate_id()[:8]}"
    title = payload.title or f"{payload.courseId} Assessment ({payload.totalMarks} Marks)"

    # Initialize a new run trace for this assessment
    run_trace = await tracker.create_run(assessment_id=aid, course_id=payload.courseId)

    assessment = Assessment(
        id=aid,
        courseId=payload.courseId,
        title=title,
        request=payload.request,
        totalMarks=payload.totalMarks,
        durationMins=payload.durationMins,
        numVersions=payload.numVersions,
        qTypes=payload.qTypes or ["mcq", "short_answer"],
        typeConfig=payload.typeConfig,
        status="draft",
        runId=run_trace.id,
        createdBy=current_user.email,
        createdByUid=current_user.uid,
    )
    await db.set("assessments", aid, assessment.model_dump())
    await log_audit(
        actor_uid=current_user.uid,
        action="create_assessment",
        entity="assessments",
        entity_id=aid,
        after=assessment.model_dump(),
    )
    await log_event(
        event_type="assessment_created",
        user_role=current_user.role,
        assessment_id=aid,
        meta={"marks": payload.totalMarks, "versions": payload.numVersions},
    )
    return assessment


@router.get("/{assessment_id}", response_model=Assessment)
async def get_assessment(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
):
    return Assessment(**await get_visible_assessment(assessment_id, current_user))


# Everything built on a paper: keyed by its id, or carrying its assessmentId. Audit logs are kept.
_CHILD_BY_ID = ("blueprints", "equivalenceReports", "moderation")
_CHILD_BY_FIELD = ("items", "flags", "versions", "runs", "notifications")


async def delete_assessment_data(assessment_id: str) -> Dict[str, int]:
    counts = {}
    for coll in _CHILD_BY_FIELD:
        docs = await db.query(coll, filters=[("assessmentId", "==", assessment_id)])
        await asyncio.gather(*[db.delete(coll, d["id"]) for d in docs])
        counts[coll] = len(docs)
    for coll in _CHILD_BY_ID:
        await db.delete(coll, assessment_id)
    await db.delete("assessments", assessment_id)
    return counts


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: str,
    current_user: User = Depends(require_role(["lecturer"])),
):
    """The paper's lecturer may delete it from their own module, unless it is in moderation or approved."""
    doc = await get_editable_assessment(assessment_id, current_user)
    require_course_owner(await db.get("courses", doc.get("courseId", "")) or {}, current_user)
    await delete_assessment_data(assessment_id)
    await log_audit(
        actor_uid=current_user.uid,
        action="delete_assessment",
        entity="assessments",
        entity_id=assessment_id,
        before=doc,
    )


@router.post("/{assessment_id}/submit", response_model=Assessment)
async def submit_for_moderation(
    assessment_id: str,
    current_user: User = Depends(require_role(["lecturer"])),
):
    """The lecturer hands a finished paper to its module's moderator and notifies them."""
    doc = await get_visible_assessment(assessment_id, current_user)
    if not is_owner(doc, current_user):
        raise HTTPException(status_code=403, detail="Only the lecturer who created this paper can submit it")
    if doc.get("status") not in SUBMITTABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Assemble the paper versions before submitting it for moderation",
        )

    # The moderator is chosen per module, so one lecturer's papers can go to different moderators.
    course_id = doc.get("courseId", "")
    moderator_uid = await module_moderator_uid(course_id)
    if not moderator_uid:
        raise HTTPException(
            status_code=409,
            detail=f"No active moderator is assigned to module {course_id}. Ask an administrator to assign one.",
        )
    moderator = await db.get("users", moderator_uid)

    resubmission = doc.get("status") == "changes_requested"
    updated = await db.update(
        "assessments",
        assessment_id,
        {
            "status": "in_moderation",
            "moderatorUid": moderator_uid,
            "submittedAt": current_time_iso(),
            "createdByUid": doc.get("createdByUid") or current_user.uid,
        },
    )

    # A resubmission reopens the decision; the moderator's earlier comments stay as history.
    record = await db.get("moderation", assessment_id)
    if record and record.get("decision"):
        record.update({"decision": None, "decidedBy": None, "decidedAt": None, "updatedAt": current_time_iso()})
        await db.set("moderation", assessment_id, record)

    await notify(
        moderator_uid,
        "submitted_for_moderation",
        "Paper resubmitted for moderation" if resubmission else "New paper for moderation",
        f"{current_user.displayName} submitted \"{doc.get('title')}\" for your review.",
        assessment_id=assessment_id,
        actor_name=current_user.displayName,
    )
    await log_audit(
        actor_uid=current_user.uid,
        action="submit_for_moderation",
        entity="assessments",
        entity_id=assessment_id,
        before={"status": doc.get("status")},
        after={"status": "in_moderation", "moderatorUid": moderator_uid},
    )
    await log_event(
        event_type="submitted_for_moderation",
        user_role=current_user.role,
        assessment_id=assessment_id,
        meta={"moderator": moderator.get("email"), "resubmission": resubmission},
    )
    return Assessment(**(updated or doc))
