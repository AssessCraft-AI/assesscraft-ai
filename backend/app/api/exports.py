import asyncio
from typing import Literal
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import JSONResponse
from app.models import User
from app.services.firestore import db
from app.services import storage
from app.tools.events import log_event
from app.auth import get_current_user
from app.api.assessments import get_visible_assessment
from app.tools.exporters import (
    render_exam_pdf,
    render_marking_guide_pdf,
    render_moodle_xml,
    render_clo_matrix_csv,
)

router = APIRouter(prefix="/assessments/{assessment_id}", tags=["exports"])


async def _deliver(
    assessment_id: str, filename: str, content, media_type: str, delivery: str
) -> Response:
    """Signed URL when Cloud Storage is configured (private object, 15 min link); else stream bytes."""
    data = content.encode("utf-8") if isinstance(content, str) else content
    if delivery != "direct" and storage.is_configured():
        url = await storage.upload_and_sign(f"exports/{assessment_id}/{filename}", data, filename, media_type)
        if url:
            return JSONResponse(
                {"signedUrl": url, "filename": filename, "expiresInSeconds": storage.SIGNED_URL_TTL_MINUTES * 60}
            )
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export")
async def export_assessment(
    assessment_id: str,
    format: Literal["pdf", "keys", "moodle_xml", "clo_csv"] = Query("pdf"),
    version: str = Query("A"),
    delivery: Literal["auto", "direct"] = Query("auto"),
    current_user: User = Depends(get_current_user),
):
    assessment = await get_visible_assessment(assessment_id, current_user)

    course_id = assessment.get("courseId", "CS2040")
    course = await db.get("courses", course_id)

    # Fetch version item IDs
    versions = await db.query("versions", filters=[("assessmentId", "==", assessment_id)])
    version_doc = next((v for v in versions if v.get("label") == version), None)

    # No fallback to the candidate pool: that printed rejected drafts under a real version label.
    if not version_doc:
        raise HTTPException(status_code=404, detail=f"Version {version} has not been assembled")
    items = [i for i in await asyncio.gather(*[db.get("items", iid) for iid in version_doc.get("itemIds", [])]) if i]

    is_approved = assessment.get("status") == "approved"
    watermark = "OFFICIAL" if is_approved else "CONFIDENTIAL – DRAFT"

    await log_event(
        event_type="assessment_exported",
        user_role=current_user.role,
        assessment_id=assessment_id,
        meta={"format": format, "version": version, "watermark": watermark, "itemCount": len(items)},
    )

    if format == "pdf":
        pdf_bytes = render_exam_pdf(
            assessment=assessment,
            version_label=version,
            items=items,
            course=course,
        )
        return await _deliver(
            assessment_id, f"{assessment_id}_Version_{version}_Exam.pdf", pdf_bytes, "application/pdf", delivery
        )

    if format == "keys":
        keys_pdf_bytes = render_marking_guide_pdf(
            assessment=assessment,
            version_label=version,
            items=items,
            course=course,
        )
        return await _deliver(
            assessment_id, f"{assessment_id}_Version_{version}_MarkingGuide.pdf", keys_pdf_bytes, "application/pdf", delivery
        )

    if format == "moodle_xml":
        xml_content = render_moodle_xml(
            assessment=assessment,
            version_label=version,
            items=items,
            course=course,
        )
        return await _deliver(
            assessment_id, f"{assessment_id}_Version_{version}_moodle.xml", xml_content, "application/xml", delivery
        )

    if format == "clo_csv":
        csv_content = render_clo_matrix_csv(
            assessment=assessment,
            version_label=version,
            items=items,
            course=course,
        )
        return await _deliver(
            assessment_id, f"{assessment_id}_Version_{version}_alignment.csv", csv_content, "text/csv", delivery
        )

    raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")
