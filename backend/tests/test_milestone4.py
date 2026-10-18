import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.firestore import db
from app.models import Course, CLO, Topic, Assessment, Item, Option, PastItem
from app.agents.reviewer import run_reviewer_agent
from app.tools.similarity import compute_embedding


@pytest.fixture(autouse=True)
async def setup_test_data():
    # 1. Course
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
            Topic(id="t3", name="SQL Joins", cloIds=["CLO2"]),
        ],
    )
    await db.set("courses", "CS2040", course.model_dump())

    # 2. Past Exam Item (2024 Exam Q7)
    past_text = "Q7: Consider an Orders and Customers query joining on customer_id with WHERE Customers.city = 'London'. Explain why this behaves like an INNER JOIN."
    past_emb = compute_embedding(past_text)
    past_item = PastItem(
        id="past-2024-q7",
        courseId="CS2040",
        docId="doc-past-paper-2024",
        year=2024,
        text=past_text,
        embedding=past_emb,
    )
    await db.set("pastItems", "past-2024-q7", past_item.model_dump())


@pytest.mark.asyncio
async def test_reviewer_key_mismatch_and_flaw_detection():
    aid = "asm-test-rev-1"
    assessment = Assessment(
        id=aid,
        courseId="CS2040",
        title="CS2040 Reviewer Key Test",
        request="Test key mismatch detection",
        totalMarks=100,
        status="pool_ready",
        runId="run-rev-1",
        createdBy="lecturer@demo",
    )
    await db.set("assessments", aid, assessment.model_dump())

    # Item with Intentionally Inverted Key:
    # Question is about weak entity discriminator where correct answer is A, but author assigned C
    item_bad_key = Item(
        id="item-flawed-key",
        assessmentId=aid,
        stem="When modeling a weak entity set in an ER schema, which attribute component is required alongside the identifying relationship's primary key to uniquely identify an entity?",
        options=[
            Option(id="A", text="Partial key (discriminator)"),
            Option(id="B", text="Surrogate foreign key"),
            Option(id="C", text="Multi-valued composite key"),
            Option(id="D", text="Derived timestamp attribute"),
        ],
        key="C",  # WRONG KEY: Should be A
        rationale="A weak entity requires a partial key (discriminator). Option A is correct.",
        qType="mcq",
        marks=2,
        cloId="CLO1",
        topicId="t1",
        bloom="understand",
        status="candidate",
        embedding=compute_embedding("When modeling a weak entity set in an ER schema, which attribute component is required"),
    )
    await db.set("items", item_bad_key.id, item_bad_key.model_dump())

    # Item with Uncapitalized Negative Word ("not" instead of "NOT")
    item_flaw = Item(
        id="item-flawed-stem",
        assessmentId=aid,
        stem="Which of the following is not a property of relational transactions?",
        options=[
            Option(id="A", text="Atomicity"),
            Option(id="B", text="Linearity"),
            Option(id="C", text="Isolation"),
            Option(id="D", text="Durability"),
        ],
        key="B",
        rationale="Linearity is not an ACID property.",
        qType="mcq",
        marks=2,
        cloId="CLO1",
        topicId="t1",
        bloom="remember",
        status="candidate",
        embedding=compute_embedding("Which of the following is not a property of relational transactions?"),
    )
    await db.set("items", item_flaw.id, item_flaw.model_dump())

    # Run Reviewer Agent
    flags = await run_reviewer_agent(aid, run_id="run-rev-1")
    assert len(flags) >= 2

    # Verify Key Mismatch Flag
    key_flags = [f for f in flags if f.type == "key_mismatch" and f.itemId == "item-flawed-key"]
    assert len(key_flags) == 1
    assert key_flags[0].severity == "high"
    assert "Author key is 'C'" in key_flags[0].detail
    assert "'A'" in key_flags[0].detail

    # Verify Item Flaw Flag
    flaw_flags = [f for f in flags if f.type == "item_flaw" and f.itemId == "item-flawed-stem"]
    assert len(flaw_flags) == 1
    assert "Negative phrasing" in flaw_flags[0].detail


@pytest.mark.asyncio
async def test_reviewer_past_exam_and_pool_duplicate_detection():
    aid = "asm-test-rev-2"
    assessment = Assessment(
        id=aid,
        courseId="CS2040",
        title="CS2040 Duplicate Test",
        request="Test duplicate detection against 2024 exam",
        totalMarks=100,
        status="pool_ready",
        runId="run-rev-2",
        createdBy="lecturer@demo",
    )
    await db.set("assessments", aid, assessment.model_dump())

    # 1. Near duplicate of 2024 Exam Q7
    stem_dup_past = "Consider an Orders and Customers query joining on customer_id with WHERE Customers.city = 'London'. Explain why this behaves like an INNER JOIN."
    item_dup_past = Item(
        id="item-dup-past-1",
        assessmentId=aid,
        stem=stem_dup_past,
        key="A",
        rationale="WHERE clause filters out NULLs.",
        qType="mcq",
        marks=2,
        cloId="CLO2",
        topicId="t3",
        bloom="apply",
        status="candidate",
        embedding=compute_embedding(stem_dup_past),
    )
    await db.set("items", item_dup_past.id, item_dup_past.model_dump())

    # 2. Pairwise pool duplicates
    stem_pair_a = "In an Entity-Relationship diagram, which relationship constraint specifies that every entity instance MUST participate in a relationship?"
    stem_pair_b = "In an Entity-Relationship diagram, which relationship constraint specifies that every entity instance MUST participate in a relationship instance?"

    item_pair_a = Item(
        id="item-pair-a",
        assessmentId=aid,
        stem=stem_pair_a,
        key="A",
        rationale="Total participation.",
        qType="mcq",
        marks=2,
        cloId="CLO1",
        topicId="t1",
        bloom="remember",
        status="candidate",
        embedding=compute_embedding(stem_pair_a),
    )
    item_pair_b = Item(
        id="item-pair-b",
        assessmentId=aid,
        stem=stem_pair_b,
        key="A",
        rationale="Total participation.",
        qType="mcq",
        marks=2,
        cloId="CLO1",
        topicId="t1",
        bloom="remember",
        status="candidate",
        embedding=compute_embedding(stem_pair_b),
    )
    await db.set("items", item_pair_a.id, item_pair_a.model_dump())
    await db.set("items", item_pair_b.id, item_pair_b.model_dump())

    # Run Reviewer Agent
    flags = await run_reviewer_agent(aid, run_id="run-rev-2")

    # Verify Past Exam Duplicate Flag
    past_flags = [f for f in flags if f.type == "duplicate_past" and f.itemId == "item-dup-past-1"]
    assert len(past_flags) == 1
    assert past_flags[0].severity == "high"
    assert "2024 past examination" in past_flags[0].detail

    # Verify Pool Duplicate Flag
    pool_flags = [f for f in flags if f.type == "duplicate_pool"]
    assert len(pool_flags) >= 1
    assert "near-duplicate of candidate" in pool_flags[0].detail


@pytest.mark.asyncio
async def test_reviewer_api_workflow_and_flag_resolution():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"X-Demo-Role": "lecturer"}
        aid = "asm-api-rev"

        # Create assessment & flawed item
        asm = Assessment(
            id=aid,
            courseId="CS2040",
            title="API Reviewer Assessment",
            request="Testing API review endpoints",
            totalMarks=100,
            status="pool_ready",
            runId="run-api-rev",
            createdBy="lecturer@demo",
        )
        await db.set("assessments", aid, asm.model_dump())

        flawed_item = Item(
            id="item-to-reject",
            assessmentId=aid,
            stem="Flawed question with negative not in lowercase",
            key="B",
            rationale="Explanation",
            qType="mcq",
            marks=2,
            cloId="CLO1",
            topicId="t1",
            bloom="remember",
            status="candidate",
            embedding=compute_embedding("Flawed question with negative not in lowercase"),
        )
        await db.set("items", flawed_item.id, flawed_item.model_dump())

        # 1. Trigger Review (POST 202)
        rev_resp = await ac.post(f"/assessments/{aid}/review", headers=headers)
        assert rev_resp.status_code == 202
        assert rev_resp.json()["status"] == "processing"

        # 2. Get Flags
        flags_resp = await ac.get(f"/assessments/{aid}/flags", headers=headers)
        assert flags_resp.status_code == 200
        flags_list = flags_resp.json()
        assert len(flags_list) >= 1

        # Regression: the status the reviewer writes must be one the Assessment model accepts,
        # otherwise GET /assessments/{id} 500s (the browser then reports "Failed to fetch").
        asm_resp = await ac.get(f"/assessments/{aid}", headers=headers)
        assert asm_resp.status_code == 200
        assert asm_resp.json()["status"] == "reviewed"

        flag_id = flags_list[0]["id"]

        # 3. Resolve Flag with "accepted" and "reject item"
        resolve_resp = await ac.patch(
            f"/flags/{flag_id}",
            json={"resolution": "accepted", "detail": "Accepted flag, reject flawed item"},
            headers=headers,
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["resolution"] == "accepted"

        # Verify item status was automatically updated to rejected
        item_doc = await db.get("items", "item-to-reject")
        assert item_doc["status"] == "rejected"

        # 4. Check Trace Recorded Reviewer Steps
        trace_resp = await ac.get(f"/runs/run-api-rev", headers=headers)
        assert trace_resp.status_code == 200
        trace = trace_resp.json()
        assert any(s["agent"] == "Reviewer" for s in trace["steps"])


@pytest.mark.asyncio
async def test_reviewer_3_run_ambiguity_and_alignment_detection():
    aid = "asm-test-rev-ambig"
    assessment = Assessment(
        id=aid,
        courseId="CS2040",
        title="Ambiguity & Alignment Test Assessment",
        request="Test 3-run ambiguity and alignment passes",
        totalMarks=100,
        status="pool_ready",
        runId="run-rev-ambig",
        createdBy="lecturer@demo",
    )
    await db.set("assessments", aid, assessment.model_dump())

    # 1. Item where 3 independent solves disagree (e.g. A, B, C) -> should raise "ambiguous"
    ambiguous_item = Item(
        id="item-ambiguous-stem",
        assessmentId=aid,
        stem="Which indexing strategy is universally superior across all real-world database workloads?",
        options=[
            Option(id="A", text="B+ Tree Index"),
            Option(id="B", text="Hash Index"),
            Option(id="C", text="Bitmap Index"),
            Option(id="D", text="LSM Tree"),
        ],
        key="A",
        rationale="Controversial question with no universally correct choice.",
        qType="mcq",
        marks=2,
        cloId="CLO1",
        topicId="t1",
        bloom="understand",
        status="candidate",
    )
    ambiguous_item_dict = ambiguous_item.model_dump()
    await db.set("items", ambiguous_item.id, ambiguous_item_dict)

    # 2. Item with Misaligned CLO (unknown CLO ID or marked misaligned)
    misaligned_item = Item(
        id="item-misaligned-clo",
        assessmentId=aid,
        stem="Explain the role of CSS Flexbox justify-content in frontend responsive design.",
        key="Flexbox aligns items along main axis.",
        rationale="Web design concept.",
        qType="short_answer",
        marks=4,
        cloId="CLO_UNKNOWN_WEB",
        topicId="t1",
        bloom="understand",
        status="candidate",
    )
    await db.set("items", misaligned_item.id, misaligned_item.model_dump())

    # 3. Item with Bloom Taxonomy Doubt (Simple recall marked as "evaluate")
    bloom_doubt_item = Item(
        id="item-bloom-doubt",
        assessmentId=aid,
        stem="Which of the following is the definition of a primary key?",
        options=[
            Option(id="A", text="A minimal superkey"),
            Option(id="B", text="Any foreign key"),
            Option(id="C", text="A secondary index"),
            Option(id="D", text="A NULL value"),
        ],
        key="A",
        rationale="Factual definition of primary key.",
        qType="mcq",
        marks=2,
        cloId="CLO1",
        topicId="t1",
        bloom="evaluate",  # Simple recall marked as "evaluate"
        status="candidate",
    )
    await db.set("items", bloom_doubt_item.id, bloom_doubt_item.model_dump())

    # Three independent solves that disagree: inject via the single-run solver (no hooks on items)
    from app.agents import reviewer as reviewer_module

    real_solve = reviewer_module.solve_item_single_run

    async def fake_solve(item, client=None, instruction="", run_index=0):
        if item.id == "item-ambiguous-stem":
            return ["B", "C", "D"][run_index % 3], f"Simulated run {run_index + 1}"
        return await real_solve(item, client, instruction, run_index)

    reviewer_module.solve_item_single_run = fake_solve
    try:
        flags = await run_reviewer_agent(aid, run_id="run-rev-ambig")
    finally:
        reviewer_module.solve_item_single_run = real_solve

    # Verify Ambiguous Flag
    ambig_flags = [f for f in flags if f.type == "ambiguous" and f.itemId == "item-ambiguous-stem"]
    assert len(ambig_flags) == 1
    assert ambig_flags[0].severity == "medium"
    assert "Ambiguous question" in ambig_flags[0].detail

    # Verify Misaligned CLO Flag
    clo_flags = [f for f in flags if f.type == "misaligned_clo" and f.itemId == "item-misaligned-clo"]
    assert len(clo_flags) == 1
    assert clo_flags[0].severity == "medium"

    # Verify Bloom Doubt Flag
    bloom_flags = [f for f in flags if f.type == "bloom_doubt" and f.itemId == "item-bloom-doubt"]
    assert len(bloom_flags) == 1
    assert bloom_flags[0].severity == "low"

