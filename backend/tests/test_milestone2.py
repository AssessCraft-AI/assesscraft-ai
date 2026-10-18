import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.tools.parsing import extract_document_text
from app.tools.search import search_knowledge_base
from app.agents.assistant import answer_course_query
from app.services.firestore import db
from seed.load_seed import seed_database


@pytest.mark.asyncio
async def test_seed_database_execution():
    await seed_database()
    course = await db.get("courses", "CS2040")
    assert course is not None
    assert course["code"] == "CS2040"
    assert len(course["clos"]) == 5
    assert len(course["topics"]) == 8

    docs = await db.query("documents", filters=[("courseId", "==", "CS2040")])
    assert len(docs) >= 5
    kinds = [d["kind"] for d in docs]
    assert "syllabus" in kinds
    assert "notes" in kinds
    assert "qa_manual" in kinds
    assert "past_paper" in kinds

    past_items = await db.query("pastItems", filters=[("courseId", "==", "CS2040")])
    assert len(past_items) == 45  # 15 questions x 3 years (2023, 2024, 2025)


@pytest.mark.asyncio
async def test_knowledge_assistant_outer_joins_query():
    answer, citations = await answer_course_query(
        course_id="CS2040",
        question="Was a question on outer joins used in previous exams?",
    )
    assert len(citations) >= 1
    # Check that citation cites 2024 or past exam
    citation_titles = " ".join([c.title or "" for c in citations])
    assert "2024" in citation_titles or "Exam" in citation_titles
    assert "outer join" in answer.lower()


@pytest.mark.asyncio
async def test_knowledge_assistant_qa_manual_repeat_paper():
    answer, citations = await answer_course_query(
        course_id="CS2040",
        question="What does the QA manual require for repeat papers?",
    )
    assert len(citations) >= 1
    assert "repeat" in answer.lower() or "equivalence" in answer.lower()


@pytest.mark.asyncio
async def test_text_parsing_markdown_and_plain():
    raw_md = b"# CS2040 Syllabus\nCourse Learning Outcomes"
    parsed = extract_document_text(raw_md, "test.md")
    assert "CS2040 Syllabus" in parsed
    assert "Course Learning Outcomes" in parsed


@pytest.mark.asyncio
async def test_assistant_api_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/courses/CS2040/assistant",
            json={"question": "Was a question on outer joins used in previous exams?"},
            headers={"x-demo-user": "lecturer@demo"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data
    assert len(data["citations"]) >= 1


@pytest.mark.asyncio
async def test_local_search_cites_relevant_passage_from_full_text():
    filler = "Introductory administrative notes. " * 60  # pushes the relevant text past the 600-char snippet
    await db.set("documents", "doc-passage-test", {
        "courseId": "PASSAGE101",
        "title": "Week 9 Notes",
        "kind": "notes",
        "contentSnippet": filler[:600],
        "fullText": filler + "Photosynthesis converts light energy into chemical energy in chloroplasts.",
    })
    citations = await search_knowledge_base("photosynthesis chloroplasts", course_id="PASSAGE101", top_k=3)
    assert citations and "Photosynthesis" in citations[0].snippet
