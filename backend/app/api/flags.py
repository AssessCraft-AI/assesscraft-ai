import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from app.models import Flag, FlagResolutionRequest, User
from app.services.firestore import db
from app.services.audit import log_audit
from app.services.traces import tracker
from app.tools.events import log_event
from app.auth import get_current_user, require_role
from app.agents.orchestrator import execute_workflow_stage
from app.api.assessments import get_editable_assessment, get_visible_assessment, reopen_assembly

router = APIRouter(tags=["flags"])


@router.get("/assessments/{assessment_id}/flags", response_model=List[Flag])
async def list_flags(
    assessment_id: str,
    type_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    await get_visible_assessment(assessment_id, current_user)
    filters = [("assessmentId", "==", assessment_id)]
    if type_filter:
        filters.append(("type", "==", type_filter))
    docs = await db.query("flags", filters=filters)
    return [Flag(**d) for d in docs]


@router.post("/assessments/{assessment_id}/review", status_code=status.HTTP_202_ACCEPTED)
async def review_assessment(
    assessment_id: str,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    assessment = await get_editable_assessment(assessment_id, current_user)

    run_id = assessment.get("runId") or f"run-review-{assessment_id}"
    await execute_workflow_stage("review", assessment_id, run_id)

    return {
        "status": "processing",
        "runId": run_id,
        "message": "Reviewer agent initiated",
    }


@router.patch("/flags/{flag_id}", response_model=Flag)
async def resolve_flag(
    flag_id: str,
    payload: FlagResolutionRequest,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    flag_data = await db.get("flags", flag_id)
    if not flag_data:
        raise HTTPException(status_code=404, detail="Flag not found")
    assessment = await get_editable_assessment(flag_data.get("assessmentId", ""), current_user)

    before = dict(flag_data)
    flag_data["resolution"] = payload.resolution
    flag_data["resolvedBy"] = current_user.email
    note = f" | Note: {payload.detail}" if payload.detail else ""
    # Re-deciding a flag must not stack the same note again.
    if note and note not in flag_data.get("detail", ""):
        flag_data["detail"] = f"{flag_data.get('detail', '')}{note}"

    saved = await db.set("flags", flag_id, flag_data)

    # Automated Item Action on Resolution
    item_id = flag_data.get("itemId")
    if item_id:
        if payload.resolution == "accepted":
            detail_str = (payload.detail or "").lower()
            if "reject" in detail_str:
                # Reject flawed or duplicate item
                await db.update("items", item_id, {"status": "rejected"})
                await reopen_assembly(assessment, item_id)
            elif "adopt" in detail_str:
                # Extract solved key from detail or flag evidence (e.g., "adopt key B" or "independent solve determined 'B'")
                match = re.search(r"adopt(?:ed)? key ([A-D])", detail_str, re.IGNORECASE) or \
                        re.search(r"determined '([A-D])'", flag_data.get("detail", ""), re.IGNORECASE)
                if match:
                    new_key = match.group(1).upper()
                    await db.update("items", item_id, {"key": new_key, "bloomConfirmed": True})

    await log_audit(
        actor_uid=current_user.uid,
        action="resolve_flag",
        entity="flags",
        entity_id=flag_id,
        before=before,
        after=saved,
    )
    await log_event(
        event_type="flag_resolved",
        user_role=current_user.role,
        assessment_id=flag_data.get("assessmentId"),
        flag_type=flag_data.get("type"),
        resolution=payload.resolution,
    )
    return Flag(**saved)
