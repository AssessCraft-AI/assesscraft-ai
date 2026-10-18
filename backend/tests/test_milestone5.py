import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.firestore import db
from app.models import (
    Course,
    CLO,
    Topic,
    Assessment,
    Blueprint,
    BlueprintCell,
    Item,
    Option,
    Flag,
)
from app.agents.solver import run_solver_agent
from app.tools.solver import assemble_paper_versions


@pytest.fixture(autouse=True)
async def setup_test_data():
    course = Course(
        id="CS2040",
        code="CS2040",
        title="Database Systems",
        ownerUid="demo-lecturer-uid",
        confirmed=True,
        clos=[
            CLO(id="CLO1", text="Relational Modeling", bloomLevel="create"),
            CLO(id="CLO2", text="SQL & Joins", bloomLevel="apply"),
        ],
        topics=[
            Topic(id="t1", name="ER Modeling", cloIds=["CLO1"]),
            Topic(id="t2", name="Relational Algebra", cloIds=["CLO1"]),
            Topic(id="t3", name="SQL Joins", cloIds=["CLO2"]),
        ],
    )
    await db.set("courses", "CS2040", course.model_dump())


def create_mock_blueprint_and_pool(assessment_id: str):
    # Blueprint: 2 cells = 4 items MCQ (8m) + 2 items Short Answer (12m) = 20 marks total
    cells = [
        BlueprintCell(cloId="CLO1", topicId="t1", bloom="understand", qType="mcq", count=4, marksEach=2),
        BlueprintCell(cloId="CLO2", topicId="t3", bloom="apply", qType="short_answer", count=2, marksEach=6),
    ]
    blueprint = Blueprint(
        assessmentId=assessment_id,
        cells=cells,
        totals={"totalMarks": 20, "totalItems": 6, "targetMarks": 20},
        valid=True,
    )

    # Candidate pool: 2.5x buffer = 10 MCQs + 5 Short Answers = 15 candidate items
    items = []
    # 10 MCQs
    for i in range(10):
        items.append(
            Item(
                id=f"mcq-{assessment_id}-{i}",
                assessmentId=assessment_id,
                stem=f"MCQ candidate question {i} regarding ER diagrams and participation constraints",
                options=[Option(id="A", text="Option A"), Option(id="B", text="Option B"), Option(id="C", text="Option C"), Option(id="D", text="Option D")],
                key="A",
                rationale="Rationale",
                qType="mcq",
                marks=2,
                cloId="CLO1",
                topicId="t1",
                bloom="understand",
                difficulty=2 + (i % 3),  # 2, 3, 4
                status="candidate",
            )
        )

    # 5 Short Answers
    for i in range(5):
        items.append(
            Item(
                id=f"sa-{assessment_id}-{i}",
                assessmentId=assessment_id,
                stem=f"Short answer problem {i} on SQL joins and window aggregation functions",
                key="Model answer",
                rationale="Scoring rubric",
                qType="short_answer",
                marks=6,
                cloId="CLO2",
                topicId="t3",
                bloom="apply",
                difficulty=3 + (i % 3),  # 3, 4, 5
                status="candidate",
            )
        )

    return blueprint, items


def test_ortools_cp_sat_assembly_zero_overlap():
    aid = "asm-solver-unit"
    blueprint, items = create_mock_blueprint_and_pool(aid)

    # Solve for 2 versions
    versions, report, status = assemble_paper_versions(items, blueprint, num_versions=2)

    assert status == "OPTIMAL"
    assert len(versions) == 2
    assert report.solverStatus == "OPTIMAL"

    ver_a = versions[0]
    ver_b = versions[1]

    # 1. Verify item counts
    assert len(ver_a.itemIds) == 6
    assert len(ver_b.itemIds) == 6

    # 2. Strict ZERO OVERLAP verification: A and B share no items
    set_a = set(ver_a.itemIds)
    set_b = set(ver_b.itemIds)
    overlap = set_a.intersection(set_b)
    assert len(overlap) == 0, f"Versions must have ZERO overlap, but found: {overlap}"
    assert report.deviations["zeroOverlapGuaranteed"] is True

    # 3. Verify total marks
    assert report.perVersion["A"]["totalMarks"] == 20
    assert report.perVersion["B"]["totalMarks"] == 20

    # 4. Verify difficulty balance
    diff_spread = report.deviations["difficultySpread"]
    assert diff_spread <= 0.5, f"Difficulty spread should be minimal, got {diff_spread}"


def test_ortools_exclusion_of_rejected_items():
    aid = "asm-solver-exclude"
    blueprint, items = create_mock_blueprint_and_pool(aid)

    # Mark two items as rejected / excluded
    excluded_ids = {"mcq-asm-solver-exclude-0", "sa-asm-solver-exclude-0"}
    items[0].status = "rejected"

    versions, report, status = assemble_paper_versions(
        items, blueprint, num_versions=2, excluded_item_ids=excluded_ids
    )
    assert status == "OPTIMAL"

    all_selected = set(versions[0].itemIds).union(set(versions[1].itemIds))
    for ex in excluded_ids:
        assert ex not in all_selected, f"Excluded item {ex} must not appear in any version"


@pytest.mark.asyncio
async def test_solver_agent_and_api_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"X-Demo-Role": "lecturer"}
        aid = "asm-api-solve"

        # 1. Setup Assessment, Blueprint, and Items
        asm = Assessment(
            id=aid,
            courseId="CS2040",
            title="CP-SAT Multi-Version Integration Paper",
            request="Assemble 2 versions",
            totalMarks=20,
            numVersions=2,
            status="pool_ready",
            runId="run-api-solve",
            createdBy="lecturer@demo",
        )
        await db.set("assessments", aid, asm.model_dump())

        blueprint, items = create_mock_blueprint_and_pool(aid)
        await db.set("blueprints", aid, blueprint.model_dump())

        for it in items:
            await db.set("items", it.id, it.model_dump())

        # 2. Add an unresolved high-severity flag on one item to verify agent exclusion
        flagged_item_id = items[1].id
        flag = Flag(
            id="flag-test-exclude",
            itemId=flagged_item_id,
            assessmentId=aid,
            type="key_mismatch",
            severity="high",
            detail="Conflict with key",
            evidence="Evidence",
        )
        await db.set("flags", flag.id, flag.model_dump())

        # 3. Trigger Assembly (POST 202)
        resp = await ac.post(f"/assessments/{aid}/assemble", headers=headers)
        assert resp.status_code == 202
        assert resp.json()["status"] == "processing"

        # 4. Fetch Versions
        v_resp = await ac.get(f"/assessments/{aid}/versions", headers=headers)
        assert v_resp.status_code == 200
        v_list = v_resp.json()
        assert len(v_list) == 2

        ver_a = v_list[0]
        ver_b = v_list[1]
        assert ver_a["label"] == "A"
        assert ver_b["label"] == "B"

        # Check zero overlap
        set_a = set(ver_a["itemIds"])
        set_b = set(ver_b["itemIds"])
        assert len(set_a.intersection(set_b)) == 0

        # Check that flagged item was excluded
        assert flagged_item_id not in set_a
        assert flagged_item_id not in set_b

        # 5. Fetch Equivalence Report
        eq_resp = await ac.get(f"/assessments/{aid}/equivalence", headers=headers)
        assert eq_resp.status_code == 200
        eq_data = eq_resp.json()
        assert eq_data["solverStatus"] == "OPTIMAL"
        assert eq_data["deviations"]["zeroOverlapGuaranteed"] is True
        assert len(eq_data["guaranteed"]) >= 3

        # 6. Fetch Version Items
        ver_items_resp = await ac.get(
            f"/assessments/{aid}/versions/{ver_a['id']}/items", headers=headers
        )
        assert ver_items_resp.status_code == 200
        ver_items = ver_items_resp.json()
        assert len(ver_items) == 6
        assert all(it["id"] in set_a for it in ver_items)

        # 7. Check Run Trace
        trace_resp = await ac.get(f"/runs/run-api-solve", headers=headers)
        assert trace_resp.status_code == 200
        trace = trace_resp.json()
        assert any(s["agent"] == "Solver" for s in trace["steps"])
