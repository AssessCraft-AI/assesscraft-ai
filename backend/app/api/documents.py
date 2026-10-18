import asyncio
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from app.models import Document, DocKind, User, generate_id
from app.services.firestore import db
from app.services import storage
from app.services.audit import log_audit
from app.services.traces import tracker
from app.tools.events import log_event
from app.auth import get_current_user, require_role
from app.api.courses import get_accessible_course, require_course_owner

# Syllabi and past papers are a few MB; this bounds memory per request and the OCR bill.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

router = APIRouter(prefix="/courses/{course_id}/documents", tags=["documents"])


@router.get("", response_model=List[Document])
async def list_documents(course_id: str, current_user: User = Depends(get_current_user)):
    await get_accessible_course(course_id, current_user)
    docs = await db.query("documents", filters=[("courseId", "==", course_id)])
    return [Document(**d) for d in docs]


@router.post("", response_model=Document, status_code=status.HTTP_201_CREATED)
async def upload_document(
    course_id: str,
    file: UploadFile = File(...),
    kind: DocKind = Form("syllabus"),
    year: Optional[int] = Form(None),
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    course = await db.get("courses", course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    require_course_owner(course, current_user)

    from app.tools.parsing import extract_document_text
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    # PDF parsing and Document AI OCR are blocking; off the event loop so other requests keep running.
    text_content = await asyncio.to_thread(extract_document_text, content, file.filename or "uploaded_file.txt")

    doc_id = f"doc-{generate_id()[:8]}"
    safe_name = (file.filename or "uploaded_file.txt").replace("/", "_")
    gcs_uri = await storage.upload_bytes(
        f"documents/{course_id}/{doc_id}/{safe_name}", content, file.content_type or "application/octet-stream"
    )
    text_gcs_uri = (
        await storage.upload_bytes(
            f"documents/{course_id}/{doc_id}/extracted.txt", text_content.encode("utf-8"), "text/plain"
        )
        if text_content
        else None
    )
    document = Document(
        id=doc_id,
        courseId=course_id,
        title=file.filename or f"Document {doc_id}",
        kind=kind,
        year=year,
        status="indexed",
        contentSnippet=text_content[:600] if text_content else None,
        searchDocId=f"search-{doc_id}",
        gcsUri=gcs_uri,
        textGcsUri=text_gcs_uri,
    )

    # fullText feeds DocIntel and grounding search; the 600-char snippet alone starved both.
    await db.set("documents", doc_id, {**document.model_dump(), "fullText": (text_content or "")[:300_000]})
    await log_audit(
        actor_uid=current_user.uid,
        action="upload_document",
        entity="documents",
        entity_id=doc_id,
        after=document.model_dump(),
    )
    await log_event(
        event_type="document_uploaded",
        user_role=current_user.role,
        meta={"course_id": course_id, "kind": kind, "title": document.title},
    )
    return document


extract_router = APIRouter(prefix="/courses/{course_id}", tags=["doc-intel"])


@extract_router.post("/extract")
async def trigger_extraction(
    course_id: str,
    current_user: User = Depends(require_role(["lecturer", "moderator"])),
):
    course = await db.get("courses", course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    require_course_owner(course, current_user)

    run_trace = await tracker.create_run(course_id=course_id, workflow="doc_intel_extraction")

    # Runs inside the request: Cloud Run throttles CPU once a response is sent, which stalls background tasks.
    from app.agents.doc_intel import run_doc_intel_extraction
    try:
        result = await run_doc_intel_extraction(course_id, run_trace.id)
    except ValueError as e:
        await tracker.complete_run(run_trace.id, status="failed")
        raise HTTPException(status_code=422, detail=str(e))
    await tracker.complete_run(run_trace.id)

    return {
        "status": "completed",
        "runId": run_trace.id,
        "clos": len(result.clos),
        "topics": len(result.topics),
        "pastQuestions": len(result.pastQuestions),
    }
