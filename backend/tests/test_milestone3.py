import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.firestore import db
from app.models import Course, CLO, Topic, Assessment
from app.agents.blueprint import run_blueprint_agent
from app.agents.item_writer import run_item_writer_agent
from app.tools.blueprint_rules import validate_blueprint, repair_blueprint


@pytest.fixture(autouse=True)
async def setup_test_data():
    # Setup test course CS2040
    course = Course(
        id="CS2040",
        code="CS2040",
        title="Database Systems",
        ownerUid="demo-lecturer-uid",
        confirmed=True,
        clos=[
            CLO(id="CLO1", text="Relational Modeling", bloomLevel="create"),
            CLO(id="CLO2", text="SQL & Joins", bloomLevel="apply"),
            CLO(id="CLO3", text="Transactions & ACID", bloomLevel="analyse"),
            CLO(id="CLO4", text="Indexing & Performance", bloomLevel="evaluate"),
            CLO(id="CLO5", text="Normalization & BCNF", bloomLevel="apply"),
        ],
        topics=[
            Topic(id="t1", name="ER Modeling", cloIds=["CLO1"]),
            Topic(id="t2", name="Relational Algebra", cloIds=["CLO1"]),
            Topic(id="t3", name="SQL Joins", cloIds=["CLO2"]),
            Topic(id="t4", name="Subqueries", cloIds=["CLO2"]),
            Topic(id="t5", name="Transactions", cloIds=["CLO3"]),
            Topic(id="t6", name="B+ Tree Indexing", cloIds=["CLO4"]),
            Topic(id="t7", name="Normalization", cloIds=["CLO5"]),
            Topic(id="t8", name="Crash Recovery", cloIds=["CLO3"]),
        ],
    )
    await db.set("courses", "CS2040", course.model_dump())


@pytest.mark.asyncio
async def test_blueprint_agent_and_rules():
    # 1. Create draft assessment
    assessment = Assessment(
        id="asm-test-bp-1",
        courseId="CS2040",
        title="CS2040 Final Exam 2026",
        request="Create 100-mark final exam covering all 5 CLOs",
        totalMarks=100,
        durationMins=120,
        numVersions=2,
        status="draft",
        runId="run-test-bp-1",
        createdBy="lecturer@demo",
    )
    await db.set("assessments", "asm-test-bp-1", assessment.model_dump())

    # 2. Run Blueprint Agent
    blueprint = await run_blueprint_agent("asm-test-bp-1", run_id="run-test-bp-1")
    assert blueprint.assessmentId == "asm-test-bp-1"
    assert blueprint.valid is True
    assert blueprint.totals["totalMarks"] == 100
    assert len(blueprint.cells) > 0

    # Verify assessment status was updated to blueprint_ready
    asm_doc = await db.get("assessments", "asm-test-bp-1")
    assert asm_doc["status"] == "blueprint_ready"

    # Verify run trace was recorded
    trace = await db.get("runs", "run-test-bp-1")
    assert trace is not None
    assert any(step["agent"] == "Blueprint" for step in trace["steps"])


@pytest.mark.asyncio
async def test_item_writer_agent_and_grounding():
    # 1. Create assessment with ready blueprint
    assessment = Assessment(
        id="asm-test-writer-1",
        courseId="CS2040",
        title="CS2040 Midterm Exam",
        request="Balanced assessment with MCQs and Short Answer",
        totalMarks=100,
        durationMins=120,
        numVersions=2,
        status="blueprint_ready",
        runId="run-test-writer-1",
        createdBy="lecturer@demo",
    )
    await db.set("assessments", "asm-test-writer-1", assessment.model_dump())

    # Generate blueprint first
    await run_blueprint_agent("asm-test-writer-1", run_id="run-test-writer-1")

    # 2. Run Item Writer Agent
    items = await run_item_writer_agent("asm-test-writer-1", run_id="run-test-writer-1")
    assert len(items) > 0

    # 3. Verify quality and grounding constraints
    for item in items[:10]:
        assert item.assessmentId == "asm-test-writer-1"
        assert item.stem
        assert len(item.sourceCitations) > 0, f"Item {item.id} must have grounding citations"
        assert item.embedding is not None, f"Item {item.id} must have vector embedding"
        assert len(item.embedding) == 768

        if item.qType == "mcq":
            assert len(item.options) == 4, f"MCQ {item.id} must have exactly 4 options"
            assert item.key in ["A", "B", "C", "D"]
            assert item.rationale, f"MCQ {item.id} must have distractor rationales"
            # Verify no forbidden phrases
            option_texts = [o.text.lower() for o in item.options]
            for text in option_texts:
                assert "all of the above" not in text
                assert "none of the above" not in text
        else:
            assert item.qType == "short_answer"
            assert item.rationale, f"Short answer {item.id} must have scoring rubric"

    # Verify assessment status is pool_ready
    asm_doc = await db.get("assessments", "asm-test-writer-1")
    assert asm_doc["status"] == "pool_ready"

    # Verify trace contains ItemWriter steps
    trace = await db.get("runs", "run-test-writer-1")
    assert any(step["agent"] == "ItemWriter" for step in trace["steps"])


@pytest.mark.asyncio
async def test_api_milestone3_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"X-Demo-Role": "lecturer"}

        # 1. Create Assessment
        resp = await ac.post(
            "/assessments",
            json={
                "courseId": "CS2040",
                "title": "CS2040 Integration Test Paper",
                "request": "100 marks exam on SQL and Transactions",
                "totalMarks": 100,
                "durationMins": 120,
                "numVersions": 2,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        aid = data["id"]
        run_id = data["runId"]

        # 2. Trigger Blueprint Generation (POST 202)
        bp_resp = await ac.post(f"/assessments/{aid}/blueprint", headers=headers)
        assert bp_resp.status_code == 202
        assert bp_resp.json()["status"] == "processing"

        # Fetch blueprint
        get_bp = await ac.get(f"/assessments/{aid}/blueprint", headers=headers)
        assert get_bp.status_code == 200
        bp_data = get_bp.json()
        assert bp_data["totals"]["totalMarks"] == 100
        assert bp_data["valid"] is True

        # 3. Trigger Item Pool Generation (POST 202)
        pool_resp = await ac.post(f"/assessments/{aid}/pool", headers=headers)
        assert pool_resp.status_code == 202
        assert pool_resp.json()["status"] == "processing"

        # 4. List Items
        items_resp = await ac.get(f"/assessments/{aid}/items", headers=headers)
        assert items_resp.status_code == 200
        items_list = items_resp.json()
        assert len(items_list) > 0

        first_item = items_list[0]
        assert first_item["status"] == "candidate"

        # 5. Patch Item Status (Accept/Reject)
        patch_resp = await ac.patch(
            f"/items/{first_item['id']}",
            json={"status": "accepted"},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "accepted"

        # 6. Check Run Trace
        trace_resp = await ac.get(f"/runs/{run_id}", headers=headers)
        assert trace_resp.status_code == 200
        trace_data = trace_resp.json()
        assert len(trace_data["steps"]) >= 2
        agents_seen = {s["agent"] for s in trace_data["steps"]}
        assert "Blueprint" in agents_seen
        assert "ItemWriter" in agents_seen
