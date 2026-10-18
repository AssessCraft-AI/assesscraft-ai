from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from app.models import Item, ItemUpdate, User
from app.services.firestore import db
from app.services.audit import log_audit
from app.services.traces import tracker
from app.tools.events import log_event
from app.auth import get_current_user, require_role
from app.agents.orchestrator import execute_workflow_stage
from app.api.assessments import ASSEMBLY_FIELDS, get_editable_assessment, get_visible_assessment, reopen_assembly

router = APIRouter(tags=["items"])


@router.get("/assessments/{assessment_id}/items", response_model=List[Item])
async def list_items(
    assessment_id: str,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    await get_visible_assessment(assessment_id, current_user)
    filters = [("assessmentId", "==", assessment_id)]
    if status_filter:
        filters.append(("status", "==", status_filter))
    docs = await db.query("items", filters=filters)
    return [Item(**d) for d in docs]


@router.post("/assessments/{assessment_id}/pool", status_code=status.HTTP_202_ACCEPTED)
async def generate_item_pool(
    assessment_id: str,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    assessment = await get_editable_assessment(assessment_id, current_user)

    run_id = assessment.get("runId") or f"run-writer-{assessment_id}"
    await execute_workflow_stage("pool", assessment_id, run_id)

    return {
        "status": "processing",
        "runId": run_id,
        "message": "Item writer agent initiated",
    }


@router.patch("/items/{item_id}", response_model=Item)
async def patch_item(
    item_id: str,
    payload: ItemUpdate,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    item_data = await db.get("items", item_id)
    if not item_data:
        raise HTTPException(status_code=404, detail="Item not found")
    assessment = await get_editable_assessment(item_data.get("assessmentId", ""), current_user)

    before = dict(item_data)
    update_dict = payload.model_dump(exclude_unset=True)
    item_data.update(update_dict)

    saved = await db.set("items", item_id, item_data)
    if any(before.get(f) != saved.get(f) for f in ASSEMBLY_FIELDS):
        await reopen_assembly(assessment, item_id)
    await log_audit(
        actor_uid=current_user.uid,
        action="patch_item",
        entity="items",
        entity_id=item_id,
        before=before,
        after=saved,
    )
    await log_event(
        event_type="item_edited",
        user_role=current_user.role,
        assessment_id=item_data.get("assessmentId"),
        meta={"item_id": item_id, "updated_fields": list(update_dict.keys())},
    )
    return Item(**saved)
