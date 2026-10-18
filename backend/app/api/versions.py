import asyncio
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from app.models import PaperVersion, EquivalenceReport, Item, User
from app.services.firestore import db
from app.services.audit import log_audit
from app.services.traces import tracker
from app.tools.events import log_event
from app.auth import get_current_user, require_role
from app.agents.orchestrator import execute_workflow_stage
from app.api.assessments import get_editable_assessment, get_visible_assessment

router = APIRouter(prefix="/assessments/{assessment_id}", tags=["versions"])


@router.get("/versions", response_model=List[PaperVersion])
async def list_versions(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
):
    await get_visible_assessment(assessment_id, current_user)
    docs = await db.query("versions", filters=[("assessmentId", "==", assessment_id)])
    # Sort versions alphabetically by label (A, B, C...)
    docs.sort(key=lambda x: x.get("label", ""))
    return [PaperVersion(**d) for d in docs]


@router.get("/versions/{version_id}/items", response_model=List[Item])
async def get_version_items(
    assessment_id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
):
    await get_visible_assessment(assessment_id, current_user)
    version_doc = await db.get("versions", version_id)
    if not version_doc or version_doc.get("assessmentId") != assessment_id:
        raise HTTPException(status_code=404, detail="Version not found")

    docs = await asyncio.gather(*[db.get("items", iid) for iid in version_doc.get("itemIds", [])])
    return [Item(**d) for d in docs if d]


@router.get("/equivalence", response_model=EquivalenceReport)
async def get_equivalence_report(
    assessment_id: str,
    current_user: User = Depends(get_current_user),
):
    await get_visible_assessment(assessment_id, current_user)
    doc = await db.get("equivalenceReports", assessment_id)
    if not doc:
        return EquivalenceReport(
            assessmentId=assessment_id,
            perVersion={},
            deviations={},
            guaranteed=["CLO Distribution", "Bloom Level Distribution", "Total Marks"],
            estimated=["Empirical Difficulty", "Cognitive Balance"],
            solverStatus="NOT_RUN",
        )
    return EquivalenceReport(**doc)


@router.post("/assemble", status_code=status.HTTP_202_ACCEPTED)
async def trigger_assembly(
    assessment_id: str,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    assessment = await get_editable_assessment(assessment_id, current_user)

    run_id = assessment.get("runId") or f"run-solver-{assessment_id}"
    await execute_workflow_stage("solver", assessment_id, run_id)

    return {
        "status": "processing",
        "runId": run_id,
        "message": "CP-SAT solver assembly initiated",
    }
