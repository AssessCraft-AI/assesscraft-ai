from fastapi import APIRouter, HTTPException, Depends
from app.models import RunTrace, User
from app.services.firestore import db
from app.auth import get_current_user
from app.api.assessments import get_visible_assessment
from app.api.courses import get_accessible_course

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}", response_model=RunTrace)
async def get_run_trace(
    run_id: str,
    current_user: User = Depends(get_current_user),
):
    doc = await db.get("runs", run_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Run trace '{run_id}' not found")
    if doc.get("assessmentId"):
        await get_visible_assessment(doc["assessmentId"], current_user)
    elif doc.get("courseId"):
        await get_accessible_course(doc["courseId"], current_user)
    return RunTrace(**doc)
