"""Second audit's must-fixes: export escaping, module read access, re-assembly after edits, safe re-extraction."""
import io
import xml.etree.ElementTree as ET

import pdfplumber
import pytest
from httpx import AsyncClient, ASGITransport

from app import auth as auth_module
from app.agents.moderation import _version_text
from app.main import app
from app.services.firestore import db
from app.tools.exporters import render_exam_pdf, render_marking_guide_pdf, render_moodle_xml
from seed.load_seed import seed_database

LECTURER = {"X-Demo-Role": "lecturer"}  # owns CS2040
OTHER = {"Authorization": "Bearer tok-other-lect"}  # a lecturer on no module

SQL_ITEM = {
    "id": "i-sql", "stem": "Which rows does SELECT * FROM emp WHERE salary <5000 AND dept <> 'HR' return? (R & S)",
    "options": [{"id": "A", "text": "a<b"}, {"id": "B", "text": "x"}, {"id": "C", "text": "y"}, {"id": "D", "text": "z"}],
    "key": "A", "rationale": "r <s", "qType": "mcq", "marks": 2, "cloId": "CLO2", "topicId": "t3", "bloom": "apply",
}
ASM = {"id": "asm-x", "title": "T", "totalMarks": 2, "durationMins": 60, "status": "assembled", "courseId": "CS2040"}


@pytest.fixture(autouse=True)
async def setup(monkeypatch):
    await seed_database()
    await db.set("users", "other-lect", {"uid": "other-lect", "email": "other@uni.edu", "displayName": "Other", "roles": ["lecturer"]})

    def fake_verify(token, *a, **k):
        if not token.startswith("tok-"):
            raise ValueError("bad token")
        return {"uid": token[4:], "email": f"{token[4:]}@uni.edu"}

    monkeypatch.setattr(auth_module.firebase_auth, "verify_id_token", fake_verify)


def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.parametrize("render, expected", [(render_exam_pdf, "salary <5000"), (render_marking_guide_pdf, "r <s")])
def test_pdf_export_keeps_sql_comparison_operators(render, expected):
    pdf = render(assessment=ASM, version_label="A", items=[SQL_ITEM], course={"code": "CS2040", "title": "DB"})
    text = "".join(p.extract_text() for p in pdfplumber.open(io.BytesIO(pdf)).pages)
    assert expected in text


def test_moodle_xml_has_plain_html_not_double_escaped_cdata():
    xml = render_moodle_xml(assessment=ASM, version_label="A", items=[SQL_ITEM], course={"code": "CS2040"})
    stem = ET.fromstring(xml).find(".//questiontext/text").text
    assert stem.startswith("<p>") and "CDATA" not in stem
    assert "salary &lt;5000" in stem  # shown as text in Moodle, not parsed as a tag


@pytest.mark.asyncio
async def test_unassigned_lecturer_cannot_read_a_module():
    async with client() as c:
        for method, path in [
            ("GET", "/courses/CS2040"),
            ("GET", "/courses/CS2040/contacts"),
            ("GET", "/courses/CS2040/documents"),
            ("POST", "/courses/CS2040/assistant"),
        ]:
            resp = await c.request(method, path, headers=OTHER, json={"question": "list past paper questions"})
            assert resp.status_code == 404, (path, resp.status_code)
        assert (await c.get("/courses/CS2040/documents", headers=LECTURER)).status_code == 200
        assert "CS2040" not in [m["id"] for m in (await c.get("/courses", headers=OTHER)).json()]


@pytest.mark.asyncio
async def test_changing_an_assembled_question_requires_reassembly():
    await db.update("assessments", "asm-demo", {"status": "assembled"})
    version = (await db.query("versions", filters=[("assessmentId", "==", "asm-demo")]))[0]
    in_paper = version["itemIds"][0]
    async with client() as c:
        # Wording edits keep the paper assembled; a rejection or mark change does not.
        assert (await c.patch(f"/items/{in_paper}", json={"stem": "Reworded stem"}, headers=LECTURER)).status_code == 200
        assert (await db.get("assessments", "asm-demo"))["status"] == "assembled"
        assert (await c.patch(f"/items/{in_paper}", json={"status": "rejected"}, headers=LECTURER)).status_code == 200
        assert (await db.get("assessments", "asm-demo"))["status"] == "reviewed"
        assert (await c.post("/assessments/asm-demo/submit", headers=LECTURER)).status_code == 409


@pytest.mark.asyncio
async def test_failed_extraction_never_writes_cs2040_outcomes_into_another_module():
    await db.set("courses", "MA101", {
        "id": "MA101", "code": "MA101", "title": "Calculus", "ownerUid": "demo-lecturer-uid",
        "clos": [{"id": "CLO1", "text": "Differentiate functions", "bloomLevel": "apply"}],
        "topics": [{"id": "t1", "name": "Derivatives", "cloIds": ["CLO1"]}], "confirmed": True,
    })
    async with client() as c:
        resp = await c.post("/courses/MA101/extract", headers=LECTURER)
    assert resp.status_code == 422
    course = await db.get("courses", "MA101")
    assert course["clos"][0]["text"] == "Differentiate functions" and course["confirmed"] is True


def test_moderation_prompt_carries_the_question_text():
    text = _version_text({"label": "A", "itemIds": ["i-sql"]}, {"i-sql": SQL_ITEM})
    assert "Version A" in text and "salary <5000" in text and "Key: A" in text
