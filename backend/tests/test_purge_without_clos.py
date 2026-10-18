import pytest

from app.services.firestore import db
from scripts.purge_assessments_without_clos import find_targets, purge


@pytest.mark.asyncio
async def test_purge_removes_only_papers_of_modules_without_outcomes():
    await db.set("courses", "EMPTY1", {"id": "EMPTY1", "code": "EMPTY1", "title": "No outcomes", "clos": [], "topics": []})
    await db.set("courses", "FULL1", {"id": "FULL1", "code": "FULL1", "title": "Has outcomes",
                                      "clos": [{"id": "CLO1", "text": "x"}], "topics": [{"id": "t1", "name": "T", "cloIds": ["CLO1"]}]})
    await db.set("assessments", "asm-bad", {"id": "asm-bad", "courseId": "EMPTY1"})
    await db.set("assessments", "asm-good", {"id": "asm-good", "courseId": "FULL1"})
    await db.set("blueprints", "asm-bad", {"assessmentId": "asm-bad"})
    await db.set("items", "it-bad", {"id": "it-bad", "assessmentId": "asm-bad"})
    await db.set("items", "it-good", {"id": "it-good", "assessmentId": "asm-good"})

    targets = [a["id"] for a in await find_targets()]
    assert "asm-bad" in targets and "asm-good" not in targets

    counts = await purge(await db.get("assessments", "asm-bad"))
    assert counts["items"] == 1
    assert await db.get("assessments", "asm-bad") is None
    assert await db.get("blueprints", "asm-bad") is None
    assert await db.get("items", "it-bad") is None
    assert await db.get("items", "it-good") is not None
