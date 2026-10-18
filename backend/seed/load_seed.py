import os
import sys
import asyncio
import re

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import Course, CLO, Topic, Document, PastItem, Assessment, generate_id
from app.auth import DEMO_USERS
from app.services.firestore import db
from app.tools.similarity import compute_embedding


async def seed_database(corpus_only: bool = False):
    """corpus_only=True seeds just the CS2040 course + reference documents/past items (for production)."""
    print("==================================================================")
    print("AssessCraft AI — Seeding Demo Database (CS2040 Database Systems)")
    print("==================================================================")

    # 1. Seed Demo Users
    if not corpus_only:
        print("--> Seeding demo users...")
        for email, user in DEMO_USERS.items():
            await db.set("users", user.uid, user.model_dump())
            print(f"    User seeded: {user.displayName} ({user.role})")

    # 2. Seed CS2040 Course
    print("--> Seeding course CS2040...")
    course = Course(
        id="CS2040",
        code="CS2040",
        title="Database Systems",
        ownerUid="demo-lecturer-uid",
        moderatorUid="demo-moderator-uid",
        confirmed=True,
        clos=[
            CLO(id="CLO1", text="Design relational database schemas from conceptual models using ER diagrams and functional dependencies.", bloomLevel="create"),
            CLO(id="CLO2", text="Write efficient declarative SQL queries including multi-table joins, subqueries, and window functions.", bloomLevel="apply"),
            CLO(id="CLO3", text="Analyze transaction isolation levels, concurrency anomalies (dirty reads, phantoms), and ACID guarantees.", bloomLevel="analyse"),
            CLO(id="CLO4", text="Evaluate B+ tree indexing strategies and query execution plans for query performance tuning.", bloomLevel="evaluate"),
            CLO(id="CLO5", text="Normalize relational relations up to Boyce-Codd Normal Form (BCNF) and 3NF.", bloomLevel="apply"),
        ],
        topics=[
            Topic(id="t1", name="Entity-Relationship (ER) Modeling", cloIds=["CLO1"]),
            Topic(id="t2", name="Relational Algebra & Schema Design", cloIds=["CLO1", "CLO5"]),
            Topic(id="t3", name="SQL Fundamentals & Complex Joins", cloIds=["CLO2"]),
            Topic(id="t4", name="Subqueries & Aggregations", cloIds=["CLO2"]),
            Topic(id="t5", name="Transactions & Concurrency Control (ACID)", cloIds=["CLO3"]),
            Topic(id="t6", name="B+ Tree Indexing & Query Tuning", cloIds=["CLO4"]),
            Topic(id="t7", name="Normalization (1NF, 2NF, 3NF, BCNF)", cloIds=["CLO5"]),
            Topic(id="t8", name="Crash Recovery & Write-Ahead Logging", cloIds=["CLO3"]),
        ],
    )
    await db.set("courses", "CS2040", course.model_dump())
    print("    Course CS2040 registered with 5 CLOs and 8 Topics.")

    # 3. Seed Course Documents
    seed_dir = os.path.dirname(__file__)
    doc_specs = [
        ("syllabus_cs2040.md", "CS2040 Course Syllabus", "syllabus", None),
        ("lecture_notes_transactions.md", "Lecture Notes: Transactions & ACID", "notes", None),
        ("lecture_notes_indexing.md", "Lecture Notes: B+ Tree Indexing", "notes", None),
        ("qa_manual_excerpt.md", "Academic QA Manual Excerpt", "qa_manual", None),
        ("past_paper_2023.md", "CS2040 Final Exam 2023", "past_paper", 2023),
        ("past_paper_2024.md", "CS2040 Final Exam 2024", "past_paper", 2024),
        ("past_paper_2025.md", "CS2040 Final Exam 2025", "past_paper", 2025),
    ]

    print("--> Seeding documents & computing embeddings...")
    for filename, title, kind, year in doc_specs:
        filepath = os.path.join(seed_dir, filename)
        if not os.path.exists(filepath):
            print(f"    WARNING: {filename} not found.")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        doc_id = f"doc-{filename.replace('.md', '').replace('_', '-')}"
        document = Document(
            id=doc_id,
            courseId="CS2040",
            title=title,
            kind=kind,
            year=year,
            status="indexed",
            contentSnippet=content[:500],
            searchDocId=f"search-{doc_id}",
        )
        await db.set("documents", doc_id, document.model_dump())
        print(f"    Document indexed: {title} ({kind})")

        # 4. Extract and Index Past Paper Items with Vector Embeddings
        if kind == "past_paper" and year:
            q_blocks = re.findall(r"\*\*Q(\d+)[^:]*:\*\*\s*(.+?)(?=\n\*\*Q\d+|\Z)", content, re.DOTALL)
            for q_num, q_text in q_blocks:
                full_item_text = f"Q{q_num}: {q_text.strip()}"
                emb = compute_embedding(full_item_text)
                past_item_id = f"past-{year}-q{q_num}"
                past_item = PastItem(
                    id=past_item_id,
                    courseId="CS2040",
                    docId=doc_id,
                    year=year,
                    text=full_item_text,
                    embedding=emb,
                )
                await db.set("pastItems", past_item_id, past_item.model_dump())

            print(f"      -> Extracted & embedded {len(q_blocks)} past items for year {year}.")

    if corpus_only:
        print("Corpus-only seeding completed (no demo users or demo assessment).")
        return

    # 5. Seed Demo Assessment "asm-demo"
    asm_demo = Assessment(
        id="asm-demo",
        courseId="CS2040",
        title="CS2040 Database Systems — Main & Repeat Exam 2026",
        request="Create a balanced 100-mark final exam covering SQL, transactions, indexing, and normalization with 2 distinct versions.",
        totalMarks=100,
        durationMins=120,
        numVersions=2,
        status="draft",
        runId="run-demo",
        createdBy="lecturer@demo",
        createdByUid="demo-lecturer-uid",
    )
    await db.set("assessments", "asm-demo", asm_demo.model_dump())
    print("    Seeded demo assessment 'asm-demo'. Generating blueprint & item pool...")

    from app.agents.blueprint import run_blueprint_agent
    from app.agents.item_writer import run_item_writer_agent
    from app.agents.reviewer import run_reviewer_agent
    from app.agents.solver import run_solver_agent

    await run_blueprint_agent("asm-demo", run_id="run-demo")
    pool_items = await run_item_writer_agent("asm-demo", run_id="run-demo")
    print(f"    Generated {len(pool_items)} candidate items for 'asm-demo'.")

    flags = await run_reviewer_agent("asm-demo", run_id="run-demo")
    print(f"    Reviewer audit completed: {len(flags)} flags identified for 'asm-demo'.")

    from app.tools.similarity import get_llm_client
    if get_llm_client() is None:
        # Offline the pool comes from a small canned bank repeated as "(Variant N)", so nearly every item is a
        # pool duplicate and the solver (which skips open duplicate_pool flags) could not fill two versions.
        for f in flags:
            if f.type == "duplicate_pool":
                await db.update("flags", f.id, {"resolution": "dismissed", "resolvedBy": "seed (offline demo bank)"})

    versions, eq_rep = await run_solver_agent("asm-demo", run_id="run-demo")
    print(f"    CP-SAT assembly completed: {len(versions)} versions assembled ({eq_rep.solverStatus}).")

    from app.agents.moderation import run_moderation_agent
    mod_record = await run_moderation_agent("asm-demo", run_id="run-demo")
    print(f"    Moderation pack generated: {len(mod_record.checklist)} checks, {len(mod_record.aiComments)} comments.")

    print("==================================================================")
    print("Database seeding completed successfully!")
    print("==================================================================")


if __name__ == "__main__":
    asyncio.run(seed_database(corpus_only="--corpus-only" in sys.argv))
