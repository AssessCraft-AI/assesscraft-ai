import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.models import CLO, Topic, BloomLevel, generate_id
from app.services.firestore import db
from app.services.traces import tracker
from app.tools.similarity import require_llm_or_fallback, compute_embeddings, get_llm_client

logger = logging.getLogger("assesscraft.doc_intel")


class ExtractedPastQuestion(BaseModel):
    year: int
    text: str
    topic: Optional[str] = None
    cloId: Optional[str] = None
    marks: int = 2


class DocIntelResult(BaseModel):
    clos: List[CLO]
    topics: List[Topic]
    pastQuestions: List[ExtractedPastQuestion] = Field(default_factory=list)


async def run_doc_intel_extraction(course_id: str, run_id: Optional[str] = None) -> DocIntelResult:
    """
    Executes the DocIntel Agent to process course documents, extract CLOs & topics,
    and index past examination items with embeddings.
    """
    rid = run_id or f"run-docintel-{course_id.lower()}"
    await tracker.record_step(
        run_id=rid,
        agent="DocIntel",
        tool="parse_document",
        input_summary=f"Parsing syllabus and archive documents for {course_id}",
        output_summary="Extracting CLOs, topic taxonomy, and past paper items",
        status="running",
    )

    # 1. Fetch course documents
    docs = await db.query("documents", filters=[("courseId", "==", course_id)])
    combined_corpus = []
    for d in docs:
        body = d.get("fullText") or d.get("contentSnippet") or ""
        combined_corpus.append(f"--- Document: {d.get('title')} ({d.get('kind')}, {d.get('year') or 'n/a'}) ---\n{body[:60_000]}")

    corpus_text = "\n\n".join(combined_corpus)

    result: Optional[DocIntelResult] = None
    client = get_llm_client()

    # 2. Use the LLM if available
    if client and corpus_text:
        try:
            with open("app/agents/prompts/doc_intel.md", "r") as f:
                instruction = f.read()

            prompt = (
                f"{instruction}\n\n"
                f"Course ID: {course_id}\n\n"
                f"Course Corpus Content:\n{corpus_text[:250_000]}\n"
            )

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.LLM_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": DocIntelResult,
                    "thinking_config": {"thinking_budget": 0},
                },
            )
            parsed_json = json.loads(response.text)
            result = DocIntelResult(**parsed_json)
            logger.info("Successfully extracted outcomes using the LLM.")
        except Exception as e:
            logger.warning(f"DocIntel LLM call failed ({e}); proceeding with curriculum extractor fallback.")

    # 3. Deterministic Curricular Fallback (Guaranteed consistency for CS2040)
    if not result or not result.clos:
        # The canned outcomes are CS2040's: writing them into any other module would replace its real CLOs.
        if course_id != "CS2040":
            raise ValueError("No learning outcomes could be extracted. Upload the module's syllabus and try again.")
        require_llm_or_fallback("DocIntel agent")
        result = DocIntelResult(
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
            pastQuestions=[],
        )

    # 4. Save extracted outcomes to course
    course_data = await db.get("courses", course_id)
    if course_data:
        course_data["clos"] = [c.model_dump() for c in result.clos]
        course_data["topics"] = [t.model_dump() for t in result.topics]
        # Fresh AI outcomes replace any edited ones, so the lecturer must review and confirm them again.
        course_data["confirmed"] = False
        await db.set("courses", course_id, course_data)

    # 5. Index past items with embeddings into pastItems collection (re-extraction replaces, never duplicates)
    old_past = await db.query("pastItems", filters=[("courseId", "==", course_id)])
    await asyncio.gather(*[db.delete("pastItems", p["id"]) for p in old_past])
    embeddings = await asyncio.to_thread(compute_embeddings, [q.text for q in result.pastQuestions]) if result.pastQuestions else []
    for q, emb in zip(result.pastQuestions, embeddings):
        past_id = f"past-{generate_id()[:8]}"
        await db.set("pastItems", past_id, {
            "id": past_id,
            "courseId": course_id,
            "docId": f"past-paper-{q.year}",
            "year": q.year,
            "text": q.text,
            "embedding": emb,
        })

    await tracker.record_step(
        run_id=rid,
        agent="DocIntel",
        tool="save_course_outcomes",
        input_summary=f"Indexed {len(result.clos)} CLOs and {len(result.topics)} topics",
        output_summary="Outcomes and past items successfully indexed into Firestore and Vector store",
        status="completed",
        sources=[d.get("title", "Doc") for d in docs],
    )

    return result
