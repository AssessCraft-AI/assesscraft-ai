import pytest
import xml.etree.ElementTree as ET
import csv
import io
from httpx import AsyncClient, ASGITransport

from app.main import app
from seed.load_seed import seed_database
from app.services.firestore import db
from app.agents.moderation import run_moderation_agent


@pytest.fixture(autouse=True)
async def setup_seed_data():
    await seed_database()


@pytest.mark.asyncio
async def test_moderation_agent_generation():
    """Test Moderation Agent execution, checklist synthesis, and AI comments."""
    record = await run_moderation_agent("asm-demo", run_id="run-demo")
    assert record.assessmentId == "asm-demo"
    assert len(record.checklist) >= 5
    for comment in record.aiComments:
        assert comment.citedItemIds is not None
        assert len(comment.citedItemIds) > 0
    assert record.executiveSummary is not None
    assert "accreditation" in record.executiveSummary.lower() or "quality assurance" in record.executiveSummary.lower()
    if record.generatedBy == "fallback":
        # Offline mode must not claim checks it cannot run or invent item commentary.
        assert record.aiComments == []
        assert not next(c for c in record.checklist if c.id == "chk-04").passed
        assert not next(c for c in record.checklist if c.id == "chk-05").passed


@pytest.mark.asyncio
async def test_moderation_rbac_and_decision():
    """Test RBAC enforcement: only moderator role can approve papers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Lecturer attempts to approve -> Expect HTTP 403 Forbidden
        lecturer_headers = {"X-Demo-Role": "lecturer"}
        resp_forbidden = await client.post(
            "/assessments/asm-demo/decision",
            headers=lecturer_headers,
            json={"decision": "approved", "comment": "Lecturer self-signoff attempted."},
        )
        assert resp_forbidden.status_code == 403

        # 2. Lecturer adds a feedback comment -> Expect HTTP 200 OK
        resp_comment = await client.post(
            "/assessments/asm-demo/comments",
            headers=lecturer_headers,
            json={"text": "Checked distractor balance on Question 4; looks good."},
        )
        assert resp_comment.status_code == 200
        mod_data = resp_comment.json()
        assert any("Question 4" in c["text"] for c in mod_data["humanComments"])

        # 3. Lecturer submits the paper to their assigned moderator
        resp_submit = await client.post("/assessments/asm-demo/submit", headers=lecturer_headers)
        assert resp_submit.status_code == 200, resp_submit.text
        assert resp_submit.json()["status"] == "in_moderation"

        # 4. Moderator approves -> Expect HTTP 200 OK
        moderator_headers = {"X-Demo-Role": "moderator"}
        resp_approved = await client.post(
            "/assessments/asm-demo/decision",
            headers=moderator_headers,
            json={"decision": "approved", "comment": "Formally approved by External Examiner."},
        )
        assert resp_approved.status_code == 200
        approved_data = resp_approved.json()
        assert approved_data["decision"] == "approved"
        assert approved_data["decidedBy"] == "moderator@demo"

        # Verify assessment status updated in DB
        assessment = await db.get("assessments", "asm-demo")
        assert assessment["status"] == "approved"

        # Verify audit entry was logged
        audit_entries = await db.query("audit", filters=[("action", "==", "moderation_decision")])
        assert len(audit_entries) >= 1


@pytest.mark.asyncio
async def test_moderation_pack_goes_stale_when_flags_change():
    """A pack generated against other flags is reported stale and cannot be approved until re-run."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        lecturer_headers = {"X-Demo-Role": "lecturer"}
        fresh = await client.get("/assessments/asm-demo/moderation", headers=lecturer_headers)
        assert fresh.status_code == 200
        assert fresh.json()["stale"] is False

        flags = await db.query("flags", filters=[("assessmentId", "==", "asm-demo")])
        flag = flags[0]
        await db.update("flags", flag["id"], {"resolution": None if flag.get("resolution") else "accepted"})

        stale = await client.get("/assessments/asm-demo/moderation", headers=lecturer_headers)
        assert stale.json()["stale"] is True

        resp_submit = await client.post("/assessments/asm-demo/submit", headers=lecturer_headers)
        assert resp_submit.status_code == 200, resp_submit.text
        blocked = await client.post(
            "/assessments/asm-demo/decision",
            headers={"X-Demo-Role": "moderator"},
            json={"decision": "approved"},
        )
        assert blocked.status_code == 409

        rerun = await client.post("/assessments/asm-demo/moderation", headers={"X-Demo-Role": "moderator"})
        assert rerun.status_code == 200
        again = await client.get("/assessments/asm-demo/moderation", headers=lecturer_headers)
        assert again.json()["stale"] is False


@pytest.mark.asyncio
async def test_never_audited_paper_is_not_auto_audited_or_approvable():
    """Commenting must not silently run the QA audit, and a paper with no audit cannot be approved."""
    await db.delete("moderation", "asm-demo")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        lecturer_headers = {"X-Demo-Role": "lecturer"}
        assert (await client.get("/assessments/asm-demo/moderation", headers=lecturer_headers)).status_code == 404

        resp_comment = await client.post(
            "/assessments/asm-demo/comments", headers=lecturer_headers, json={"text": "Before the audit."}
        )
        assert resp_comment.status_code == 200
        body = resp_comment.json()
        assert body["executiveSummary"] is None and body["checklist"] == []
        assert body["stale"] is False

        assert (await client.post("/assessments/asm-demo/submit", headers=lecturer_headers)).status_code == 200
        blocked = await client.post(
            "/assessments/asm-demo/decision", headers={"X-Demo-Role": "moderator"}, json={"decision": "approved"}
        )
        assert blocked.status_code == 409
        assert "never been run" in blocked.json()["detail"]


@pytest.mark.asyncio
async def test_exports_all_formats():
    """Test all 4 assessment export formats: PDF, marking guide, Moodle XML, and CLO CSV."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-Demo-Role": "lecturer"}

        # 1. Printable Exam PDF
        resp_pdf = await client.get("/assessments/asm-demo/export?format=pdf&version=A", headers=headers)
        assert resp_pdf.status_code == 200
        assert resp_pdf.headers["content-type"] == "application/pdf"
        assert resp_pdf.content.startswith(b"%PDF-")
        assert len(resp_pdf.content) > 5000  # Multi-page compiled PDF

        # 2. Examiner's Marking Guide PDF
        resp_keys = await client.get("/assessments/asm-demo/export?format=keys&version=A", headers=headers)
        assert resp_keys.status_code == 200
        assert resp_keys.headers["content-type"] == "application/pdf"
        assert resp_keys.content.startswith(b"%PDF-")
        assert len(resp_keys.content) > 3000

        # 3. Moodle XML Quiz Bank
        resp_moodle = await client.get("/assessments/asm-demo/export?format=moodle_xml&version=A", headers=headers)
        assert resp_moodle.status_code == 200
        assert "application/xml" in resp_moodle.headers["content-type"]
        xml_text = resp_moodle.text
        # Validate XML structure
        root = ET.fromstring(xml_text)
        assert root.tag == "quiz"
        questions = root.findall("question")
        assert len(questions) > 10  # Category + multiple questions
        assert any(q.get("type") == "multichoice" for q in questions)
        assert any(q.get("type") == "essay" for q in questions)

        # 4. CLO Alignment Matrix CSV
        resp_csv = await client.get("/assessments/asm-demo/export?format=clo_csv&version=A", headers=headers)
        assert resp_csv.status_code == 200
        assert "text/csv" in resp_csv.headers["content-type"]
        csv_text = resp_csv.text
        reader = list(csv.reader(io.StringIO(csv_text)))
        assert len(reader) >= 31  # Header + 30 items
        header = reader[0]
        assert "Question Number" in header
        assert "Course Learning Outcome (CLO)" in header
        assert "Bloom Taxonomy Level" in header
        assert "Source Citation Document" in header


@pytest.mark.asyncio
async def test_export_uses_signed_url_when_storage_is_configured(monkeypatch):
    """With Cloud Storage configured the export endpoint returns a signed URL, not raw bytes."""
    from app.services import storage

    uploaded = {}

    async def fake_upload_and_sign(path, data, filename, content_type):
        uploaded["path"], uploaded["size"] = path, len(data)
        return f"https://storage.example/{path}?X-Goog-Signature=abc"

    monkeypatch.setattr(storage, "is_configured", lambda: True)
    monkeypatch.setattr(storage, "upload_and_sign", fake_upload_and_sign)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        signed = await client.get(
            "/assessments/asm-demo/export?format=clo_csv&version=A", headers={"X-Demo-Role": "lecturer"}
        )
        direct = await client.get(
            "/assessments/asm-demo/export?format=clo_csv&version=A&delivery=direct",
            headers={"X-Demo-Role": "lecturer"},
        )

    assert signed.status_code == 200
    assert signed.json()["signedUrl"].startswith("https://storage.example/exports/asm-demo/")
    assert uploaded["size"] > 0
    assert direct.headers["content-type"].startswith("text/csv")
