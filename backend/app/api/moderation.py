import asyncio

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from app.models import ModerationRecord, ModerationDecisionRequest, Comment, User, current_time_iso, generate_id
from app.services.firestore import db
from app.services.audit import log_audit
from app.services.traces import tracker
from app.tools.events import log_event
from app.auth import get_current_user, require_role
from app.agents.moderation import run_moderation_agent, inputs_key
from app.api.assessments import get_visible_assessment, is_owner, is_paper_moderator, role_on_paper
from app.services.notifications import notify

router = APIRouter(prefix="/assessments/{assessment_id}", tags=["moderation"])


class HumanCommentRequest(BaseModel):
    text: str
    citedItemIds: Optional[list[str]] = None


@router.get("/moderation", response_model=ModerationRecord)
async def get_moderation_record(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
):
    assessment = await get_visible_assessment(assessment_id, current_user)
    doc = await db.get("moderation", assessment_id)
    if not doc:
        # Generation is an explicit POST: running the (paid) agent on every page load cost tokens and 500'd before versions existed.
        raise HTTPException(status_code=404, detail="Moderation pack not generated yet")
    return ModerationRecord(**doc, stale=await _is_stale(assessment_id, doc))


@router.post("/moderation", response_model=ModerationRecord)
async def generate_moderation_pack(
    assessment_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(["moderator"])),
):
    # The QA audit is the moderator's independent check, so the paper's author never runs it.
    assessment = await get_visible_assessment(assessment_id, current_user)
    if is_owner(assessment, current_user):
        raise HTTPException(status_code=403, detail="You cannot run the QA audit on a paper you wrote")
    if not is_paper_moderator(assessment, current_user):
        raise HTTPException(status_code=403, detail="Only the moderator assigned to this paper can run its QA audit")
    if assessment.get("status") != "in_moderation":
        raise HTTPException(
            status_code=409,
            detail="The QA audit runs while the paper is in moderation, before a decision is recorded",
        )
    record = await run_moderation_agent(assessment_id)
    return record


@router.post("/comments", response_model=ModerationRecord)
async def add_moderation_comment(
    assessment_id: str,
    payload: HumanCommentRequest,
    current_user: User = Depends(get_current_user),
):
    assessment = await get_visible_assessment(assessment_id, current_user)
    await _get_or_create_record(assessment_id)

    new_comment = Comment(
        id=generate_id(),
        author=current_user.displayName or current_user.email,
        role=role_on_paper(assessment, current_user),
        text=payload.text,
        citedItemIds=payload.citedItemIds or [],
        createdAt=current_time_iso(),
    )

    # Atomic append: two people commenting at once must both keep their comment.
    await db.append("moderation", assessment_id, "humanComments", new_comment.model_dump())
    doc = await db.update("moderation", assessment_id, {"updatedAt": current_time_iso()})

    await log_audit(
        actor_uid=current_user.uid,
        action="moderation_comment_added",
        entity="moderation",
        entity_id=assessment_id,
        after={"comment": payload.text, "author": current_user.email},
    )

    return ModerationRecord(**doc, stale=await _is_stale(assessment_id, doc))


@router.post("/decision", response_model=ModerationRecord)
async def submit_moderation_decision(
    assessment_id: str,
    payload: ModerationDecisionRequest,
    current_user: User = Depends(require_role(["moderator"])),
):
    assessment = await get_visible_assessment(assessment_id, current_user)
    if is_owner(assessment, current_user):
        raise HTTPException(status_code=403, detail="You cannot moderate a paper you wrote")
    if not is_paper_moderator(assessment, current_user):
        raise HTTPException(status_code=403, detail="Only the moderator assigned to this paper can decide on it")
    if assessment.get("status") != "in_moderation":
        raise HTTPException(
            status_code=409,
            detail="This paper has not been submitted for moderation (or a decision was already recorded)",
        )

    record_data = await _get_or_create_record(assessment_id)

    if payload.decision == "approved" and not _audited(record_data):
        raise HTTPException(
            status_code=409,
            detail="The QA audit has never been run for this paper. Run it before approving.",
        )
    stale = await _is_stale(assessment_id, record_data)
    if stale and payload.decision == "approved":
        # Approving a pack that reviewed different versions or flags would sign off a paper nobody audited.
        raise HTTPException(
            status_code=409,
            detail="The moderation pack is out of date: versions or reviewer flags changed. Re-run the QA audit before approving.",
        )

    before = dict(record_data)
    if payload.comment:
        comment = Comment(
            id=generate_id(),
            author=current_user.displayName or current_user.email,
            role=role_on_paper(assessment, current_user),
            text=payload.comment,
            createdAt=current_time_iso(),
        )
        await db.append("moderation", assessment_id, "humanComments", comment.model_dump())
    # shortcut: the in_moderation check above is not transactional, so two decisions sent in the same
    # instant can both land (the later wins); move to a Firestore transaction if moderators share papers.
    now = current_time_iso()
    saved = await db.update(
        "moderation",
        assessment_id,
        {"decision": payload.decision, "decidedBy": current_user.email, "decidedAt": now, "updatedAt": now},
    )

    # Update assessment status
    new_status = "approved" if payload.decision == "approved" else "changes_requested"
    await db.update("assessments", assessment_id, {"status": new_status})

    await log_audit(
        actor_uid=current_user.uid,
        action="moderation_decision",
        entity="moderation",
        entity_id=assessment_id,
        before=before,
        after=saved,
    )
    approved = payload.decision == "approved"
    note = f" Comment: {payload.comment}" if payload.comment else ""
    await notify(
        await _lecturer_uid(assessment),
        "moderation_approved" if approved else "moderation_changes_requested",
        "Paper approved" if approved else "Changes requested",
        f"{current_user.displayName} "
        + ("approved" if approved else "requested changes to")
        + f" \"{assessment.get('title')}\".{note}",
        assessment_id=assessment_id,
        actor_name=current_user.displayName,
    )
    await log_event(
        event_type="paper_approved" if payload.decision == "approved" else "changes_requested",
        user_role=current_user.role,
        assessment_id=assessment_id,
        meta={"decision": payload.decision, "moderator": current_user.email},
    )
    return ModerationRecord(**saved, stale=stale)


def _audited(doc: dict) -> bool:
    """Only the QA audit writes the summary; a record without one holds just comments or a decision."""
    return bool(doc.get("executiveSummary"))


async def _get_or_create_record(assessment_id: str) -> dict:
    """Comments and decisions need a record to attach to, but must not silently run the (paid) audit."""
    doc = await db.get("moderation", assessment_id)
    if not doc:
        doc = await db.set("moderation", assessment_id, ModerationRecord(assessmentId=assessment_id).model_dump(exclude={"stale"}))
    return doc


async def _is_stale(assessment_id: str, doc: dict) -> bool:
    """True when the versions or open flags differ from those the pack was generated from."""
    if not _audited(doc):
        return False
    versions, flags = await asyncio.gather(
        db.query("versions", filters=[("assessmentId", "==", assessment_id)]),
        db.query("flags", filters=[("assessmentId", "==", assessment_id)]),
    )
    return doc.get("inputsKey") != inputs_key(versions, flags)


async def _lecturer_uid(assessment: dict):
    if assessment.get("createdByUid"):
        return assessment["createdByUid"]
    owners = await db.query("users", filters=[("email", "==", assessment.get("createdBy"))])
    return owners[0]["uid"] if owners else None
