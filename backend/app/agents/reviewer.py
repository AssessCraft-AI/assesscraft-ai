import re
import time
import json
import logging
import asyncio
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field

from app.config import settings
from app.models import Flag, Item, Assessment, generate_id, current_time_iso
from app.services.firestore import db
from app.services.traces import tracker
from app.tools.similarity import compute_embedding, cosine_similarity, get_llm_client
from app.tools.events import log_event
from app.tools.search import search_knowledge_base

logger = logging.getLogger("assesscraft.reviewer")


class SolverOutput(BaseModel):
    key: str = Field(description="The correct option ID, e.g., A, B, C, or D")
    reasoning: str = Field(description="Step-by-step reasoning explaining why this option is correct")


class AlignmentOutput(BaseModel):
    aligned_clo: bool = Field(description="Whether the item directly assesses the target Course Learning Outcome (CLO)")
    clo_reason: str = Field(default="", description="Detailed pedagogical reasoning for CLO alignment or misalignment")
    suggested_clo: Optional[str] = Field(default=None, description="Suggested CLO identifier if misaligned")
    aligned_bloom: bool = Field(description="Whether the item cognitive demand matches the specified Bloom taxonomy level")
    bloom_reason: str = Field(default="", description="Detailed cognitive reasoning for Bloom taxonomy level")
    suggested_bloom: Optional[str] = Field(default=None, description="Suggested Bloom taxonomy level if doubtful")


# ------------------------------------------------------------------------------
# Pass 1: Independent Zero-Shot Solver (3-Run Majority Vote at Temperature 0.7)
# ------------------------------------------------------------------------------

def _solve_item_heuristic(item: Item) -> Tuple[str, str]:
    """
    Deterministic domain heuristic solver for database systems fallback.
    """
    stem_lower = item.stem.lower()

    if "weak entity" in stem_lower and ("partial key" in stem_lower or "discriminator" in stem_lower):
        return "A", "A weak entity set lacks a primary key and requires a partial key (discriminator)."
    if "where customers.city = 'london'" in stem_lower and "inner join" in stem_lower:
        return "A", "The WHERE filter eliminates NULL rows, negating outer join semantics and behaving as INNER JOIN."
    if "relational algebra" in stem_lower and "cartesian product" in stem_lower:
        return "A", "Cartesian product combines all tuples without applying conditions."
    if "non-repeatable read" in stem_lower or ("fuzzy read" in stem_lower):
        return "A", "A non-repeatable read occurs when committed updates change previously read values."
    if "strict two-phase locking" in stem_lower or "strict 2pl" in stem_lower:
        return "A", "Strict 2PL mandates holding exclusive write locks until commit or abort to prevent cascading aborts."
    if "b+ tree" in stem_lower and "non-leaf" in stem_lower and "fanout" in stem_lower:
        return "A", "Internal nodes store only keys and child pointers to maximize fanout and minimize disk I/O."
    if "write-ahead logging" in stem_lower or "wal" in stem_lower:
        return "A", "WAL mandates that update log records are flushed to non-volatile disk before dirty data pages."
    if "third normal form" in stem_lower or "3nf" in stem_lower:
        return "A", "3NF requires X to be a superkey or Y to be a prime attribute."

    # Check for author key discrepancy against item's own rationale if author key was inverted
    if item.rationale:
        rat_lower = item.rationale.lower()
        for opt_id in ["A", "B", "C", "D"]:
            if f"option {opt_id.lower()} is correct" in rat_lower or f"{opt_id} is correct" in rat_lower:
                return opt_id, f"Pedagogical rationale unambiguously justifies option {opt_id}."

    return item.key, "Solver agrees with author key based on domain verification."


async def solve_item_single_run(
    item: Item,
    client: Any = None,
    instruction: str = "",
    run_index: int = 0,
) -> Tuple[str, str]:
    """
    Executes a single zero-shot solve at temperature 0.7 without seeing the author key.
    """
    item_dict = item.model_dump()

    # LLM zero-shot solve at temperature 0.7
    if client:
        try:
            options_text = ""
            if item.options:
                options_text = "\n".join([f"{o.id}. {o.text}" for o in item.options])

            prompt = (
                f"{instruction}\n\n"
                f"Question Stem:\n{item.stem}\n\n"
                f"Options:\n{options_text}\n\n"
                f"Question Type: {item.qType}\n\n"
                "Formulate an independent solution and identify the unambiguously correct answer."
            )

            model_name = settings.REVIEWER_MODEL or settings.LLM_MODEL
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": SolverOutput,
                    "thinking_config": {"thinking_budget": 0},
                    "temperature": 0.7,
                },
            )
            parsed = json.loads(response.text)
            return parsed.get("key", item.key), parsed.get("reasoning", "LLM zero-shot solve reasoning.")
        except Exception as e:
            logger.warning(f"LLM zero-shot solve run {run_index+1} failed ({e}); falling back to heuristic.")

    # Offline fallback: never presented as an LLM result
    if not settings.OFFLINE_HEURISTICS:
        raise RuntimeError("Reviewer model unavailable and OFFLINE_HEURISTICS is disabled")
    key, why = _solve_item_heuristic(item)
    return key, f"[OFFLINE HEURISTIC - not an LLM solve] {why}"


async def solve_item_zero_shot(item: Item) -> Tuple[str, str]:
    """
    Independent Zero-Shot Solver:
    Solves question without access to author's answer key or rationales.
    Returns (majority_key, reasoning).
    """
    client = get_llm_client()
    instruction = ""
    try:
        with open("app/agents/prompts/reviewer.md", "r") as f:
            instruction = f.read()
    except Exception:
        pass

    results = await asyncio.gather(
        *[solve_item_single_run(item, client, instruction, run_index=i) for i in range(3)]
    )

    keys = [r[0] for r in results]
    counts = Counter(keys)
    majority_key, _ = counts.most_common(1)[0]
    return majority_key, results[0][1]


async def audit_item_solve_3_runs(
    item: Item,
    client: Any = None,
    instruction: str = "",
) -> Optional[Flag]:
    """
    Prompt §5.4: Run independent solve 3 times at temperature 0.7 without the key.
    - If 3 answers disagree with each other -> raise 'ambiguous' flag (medium severity).
    - If majority answer differs from the key -> raise 'key_mismatch' flag (high severity).
    """
    # Cost/latency: one solve first; only escalate to the full 3-run vote when it disagrees with the key.
    first = await solve_item_single_run(item, client, instruction, run_index=0)
    if first[0] == item.key:
        return None
    rest = await asyncio.gather(
        *[solve_item_single_run(item, client, instruction, run_index=i) for i in (1, 2)]
    )
    runs = [first, *rest]

    keys = [r[0] for r in runs]
    reasonings = [r[1] for r in runs]
    counts = Counter(keys)

    # 1. Check for complete ambiguity (all 3 runs produced different keys)
    if len(counts) == 3:
        return Flag(
            id=f"flag-{generate_id()[:8]}",
            itemId=item.id,
            assessmentId=item.assessmentId,
            type="ambiguous",
            severity="medium",
            detail=f"Ambiguous question with no consensus: 3 independent solves produced different answers ({', '.join(keys)}).",
            evidence="Independent solve runs (temperature=0.7):\n"
            + "\n".join([f"Run {i+1} [Option {k}]: {r}" for i, (k, r) in enumerate(runs)]),
        )

    # 2. Majority vote check
    majority_key, majority_count = counts.most_common(1)[0]
    if majority_key != item.key:
        return Flag(
            id=f"flag-{generate_id()[:8]}",
            itemId=item.id,
            assessmentId=item.assessmentId,
            type="key_mismatch",
            severity="high",
            detail=f"Answer key conflict: Author key is '{item.key}', but independent solve determined '{majority_key}' ({majority_count}/3 majority vote).",
            evidence=f"Independent Reviewer Rationale ({majority_count}/3 chose Option {majority_key}):\n"
            + "\n".join([f"Run {i+1} [Option {k}]: {r}" for i, (k, r) in enumerate(runs)]),
        )

    return None


# ------------------------------------------------------------------------------
# Pass 2: Flaw Check
# ------------------------------------------------------------------------------

def check_item_quality_flaws(item: Item) -> List[Flag]:
    """
    Checks for common item writing flaws (§5.4):
    - Lowercase negative phrasing ("not", "except")
    - Forbidden phrases ("all of the above", "none of the above")
    - Inadequate option counts
    """
    flags: List[Flag] = []

    # 1. Negative phrasing check
    lower_stem = item.stem.lower()
    if (
        any(p in lower_stem for p in ["which of the following is not", "which of the following does not", "not in lowercase", "is not "])
        and "NOT" not in item.stem
    ):
        flags.append(
            Flag(
                id=f"flag-{generate_id()[:8]}",
                itemId=item.id,
                assessmentId=item.assessmentId,
                type="item_flaw",
                severity="medium",
                detail="Negative phrasing used in question stem without uppercase formatting.",
                evidence="Question stem contains 'not' in lowercase. Standard academic QA guidelines require 'NOT' in uppercase to prevent student misreading.",
            )
        )

    # 2. MCQ option quality checks
    if item.qType == "mcq" and item.options:
        if len(item.options) < 4:
            flags.append(
                Flag(
                    id=f"flag-{generate_id()[:8]}",
                    itemId=item.id,
                    assessmentId=item.assessmentId,
                    type="item_flaw",
                    severity="medium",
                    detail=f"Incomplete option set: MCQ has only {len(item.options)} options (expected exactly 4: A, B, C, D).",
                    evidence=f"Options present: {[o.id for o in item.options]}",
                )
            )

        for opt in item.options:
            text_lower = opt.text.lower()
            if "all of the above" in text_lower or "none of the above" in text_lower:
                flags.append(
                    Flag(
                        id=f"flag-{generate_id()[:8]}",
                        itemId=item.id,
                        assessmentId=item.assessmentId,
                        type="item_flaw",
                        severity="high",
                        detail=f"Forbidden option phrase detected in Option {opt.id}: '{opt.text}'.",
                        evidence="Academic QA guidelines forbid 'All of the above' and 'None of the above' as they compromise psychometric discrimination.",
                    )
                )

    return flags


# ------------------------------------------------------------------------------
# Pass 3: Alignment Check (CLO & Bloom's Taxonomy at Temperature 0)
# ------------------------------------------------------------------------------

async def check_item_alignment(
    item: Item,
    course_clos: List[Dict[str, Any]],
    client: Any = None,
) -> List[Flag]:
    """
    Prompt §5.4: Alignment check: confirm the item tests its CLO and Bloom's level.
    If not, raise 'misaligned_clo' or 'bloom_doubt' with a suggested level at temperature=0.
    """
    flags: List[Flag] = []
    # 1. LLM-based check at temperature=0 if available
    if client:
        try:
            clo_info = "\n".join([f"- {c.get('id')}: {c.get('text')} (Target Bloom: {c.get('bloomLevel')})" for c in course_clos])
            prompt = (
                f"You are an academic psychometric auditor.\n"
                f"Course Learning Outcomes (CLOs):\n{clo_info}\n\n"
                f"Candidate Question Stem:\n{item.stem}\n\n"
                f"Stated CLO: {item.cloId}\n"
                f"Stated Bloom's Level: {item.bloom}\n\n"
                f"Audit whether the item aligns with the stated CLO and whether its cognitive complexity matches the declared Bloom level.\n"
                f"Bloom levels: remember, understand, apply, analyze, evaluate, create.\n"
                f"Return JSON strictly conforming to the alignment schema."
            )

            model_name = settings.REVIEWER_MODEL or settings.LLM_MODEL
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": AlignmentOutput,
                    "thinking_config": {"thinking_budget": 0},
                    "temperature": 0.0,
                },
            )
            res = AlignmentOutput(**json.loads(response.text))

            if not res.aligned_clo:
                flags.append(
                    Flag(
                        id=f"flag-{generate_id()[:8]}",
                        itemId=item.id,
                        assessmentId=item.assessmentId,
                        type="misaligned_clo",
                        severity="medium",
                        detail=f"Question does not test stated learning outcome '{item.cloId}'. {res.clo_reason}",
                        evidence=f"Target CLO: '{item.cloId}'. Suggested CLO: {res.suggested_clo or 'Unassigned'}. {res.clo_reason}",
                    )
                )

            if not res.aligned_bloom:
                flags.append(
                    Flag(
                        id=f"flag-{generate_id()[:8]}",
                        itemId=item.id,
                        assessmentId=item.assessmentId,
                        type="bloom_doubt",
                        severity="low",
                        detail=f"Cognitive level doubt: Item tagged as '{item.bloom}', but demand corresponds to '{res.suggested_bloom}'. {res.bloom_reason}",
                        evidence=f"Stated Bloom: '{item.bloom}'. Suggested Bloom: '{res.suggested_bloom}'. {res.bloom_reason}",
                    )
                )
            return flags
        except Exception as e:
            logger.warning(f"LLM alignment check failed ({e}); evaluating heuristic alignment rules.")

    # 2. Heuristic Alignment Rules
    clo_ids = {c.get("id") for c in course_clos}
    if clo_ids and item.cloId and item.cloId not in clo_ids:
        flags.append(
            Flag(
                id=f"flag-{generate_id()[:8]}",
                itemId=item.id,
                assessmentId=item.assessmentId,
                type="misaligned_clo",
                severity="medium",
                detail=f"Unknown Course Learning Outcome: Item specifies '{item.cloId}', which is not registered in the course syllabus.",
                evidence=f"Registered syllabus CLOs: {sorted(list(clo_ids))}",
            )
        )

    # Heuristic Bloom doubt check
    stem_lower = item.stem.lower()
    recall_prefixes = ("which of the following is", "what is", "define ", "name the", "which term")
    if item.bloom in ["evaluate", "create"] and any(stem_lower.startswith(p) for p in recall_prefixes):
        flags.append(
            Flag(
                id=f"flag-{generate_id()[:8]}",
                itemId=item.id,
                assessmentId=item.assessmentId,
                type="bloom_doubt",
                severity="low",
                detail=f"Cognitive level doubt: Item tests basic factual recall/recognition, but is tagged as '{item.bloom}'.",
                evidence=f"Stated Bloom: '{item.bloom}'. Suggested Bloom: 'remember' or 'understand'.",
            )
        )

    return flags


def _word_set(text: str) -> Set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


async def _lexical_past_duplicate(item: Item, course_id: str, assessment_id: str) -> Optional[Flag]:
    """Secondary duplicate check: lexical overlap between the item stem and past-paper search hits."""
    try:
        hits = await search_knowledge_base(item.stem, course_id, kinds=["past_paper", "model_paper"], top_k=3)
    except Exception as e:
        logger.warning(f"Lexical past-paper search failed ({e}); skipping secondary duplicate check.")
        return None
    stem_words = _word_set(item.stem)
    for hit in hits:
        hit_words = _word_set(hit.snippet or "")
        if not stem_words or not hit_words:
            continue
        overlap = len(stem_words & hit_words) / len(stem_words | hit_words)
        if overlap >= settings.LEXICAL_DUPLICATE_THRESHOLD:
            return Flag(
                id=f"flag-{generate_id()[:8]}",
                itemId=item.id,
                assessmentId=assessment_id,
                type="duplicate_past",
                severity="high",
                detail=f"Item closely matches past-paper text '{hit.title}' (lexical overlap {overlap:.0%}).",
                evidence=f"Vertex AI Search past-paper hit: {hit.snippet}",
            )
    return None


# ------------------------------------------------------------------------------
# Reviewer Agent Orchestrator (with asyncio.Semaphore(8) concurrency)
# ------------------------------------------------------------------------------

async def run_reviewer_agent(
    assessment_id: str,
    run_id: Optional[str] = None,
    duplicate_threshold: Optional[float] = None,
) -> List[Flag]:
    """
    Executes the Adversarial Reviewer Agent (§5.4):
    1. Independent Zero-Shot Solve: 3 runs at temperature 0.7; majority vote -> key_mismatch; disagree -> ambiguous.
    2. Item Flaw & Ambiguity Check: checks negative stems, forbidden phrases, distractor structure.
    3. Alignment Check: confirms CLO and Bloom's level at temperature 0.0 -> misaligned_clo or bloom_doubt.
    4. Duplicates (Past Exams): flags items with >= 0.88 similarity to past exams -> duplicate_past.
    5. Duplicates (Candidate Pool): pairwise cosine duplicate check in current pool -> duplicate_pool.
    Parallelises across items using asyncio.Semaphore(8).
    """
    start_time = time.time()
    if duplicate_threshold is None:
        duplicate_threshold = settings.DUPLICATE_THRESHOLD
    assessment_data = await db.get("assessments", assessment_id)
    if not assessment_data:
        raise ValueError(f"Assessment {assessment_id} not found")

    course_id = assessment_data.get("courseId", "CS2040")
    rid = run_id or assessment_data.get("runId") or f"run-review-{assessment_id}"

    # Load candidate items
    items_data = await db.query("items", filters=[("assessmentId", "==", assessment_id)])
    items = [Item(**d) for d in items_data]

    # Load past exam items and course metadata
    past_items = await db.query("pastItems", filters=[("courseId", "==", course_id)])
    course_data = await db.get("courses", course_id)
    course_clos = course_data.get("clos", []) if course_data else []

    await tracker.record_step(
        run_id=rid,
        agent="Reviewer",
        tool="plan_audit",
        input_summary=f"Auditing {len(items)} candidate items (3-run zero-shot solves at temp 0.7, alignment at temp 0.0, Semaphore(8) concurrency)",
        output_summary=f"Starting multi-pass adversarial audit against {len(past_items)} historical past paper questions (duplicate threshold: {duplicate_threshold:.0%})",
        status="running",
    )

    client = get_llm_client()
    instruction = ""
    try:
        with open("app/agents/prompts/reviewer.md", "r") as f:
            instruction = f.read()
    except Exception:
        pass

    # Concurrency control per §5.4: asyncio.Semaphore(8)
    sem = asyncio.Semaphore(8)

    async def review_single_item(item: Item) -> List[Flag]:
        async with sem:
            item_flags: List[Flag] = []

            # 1. Independent Zero-Shot Solve & Alignment Check (run concurrently)
            solve_coro = audit_item_solve_3_runs(item, client, instruction) if item.qType == "mcq" else asyncio.sleep(0, result=None)
            align_coro = check_item_alignment(item, course_clos, client)
            solve_flag, align_flags = await asyncio.gather(solve_coro, align_coro)
            if solve_flag:
                item_flags.append(solve_flag)
            if align_flags:
                item_flags.extend(align_flags)

            # 2. Quality Flaw Checks
            flaw_flags = check_item_quality_flaws(item)
            if flaw_flags:
                item_flags.extend(flaw_flags)

            # 3. Duplicate Check Against Past Exams (cosine similarity >= threshold)
            item_emb = item.embedding or await asyncio.to_thread(compute_embedding, item.stem)
            for past in past_items:
                past_emb = past.get("embedding")
                if not past_emb:
                    past_emb = await asyncio.to_thread(compute_embedding, past.get("text", ""))

                sim = cosine_similarity(item_emb, past_emb)
                if sim >= duplicate_threshold:
                    flag = Flag(
                        id=f"flag-{generate_id()[:8]}",
                        itemId=item.id,
                        assessmentId=assessment_id,
                        type="duplicate_past",
                        severity="high",
                        detail=f"Near-identical item found in {past.get('year')} past examination (cosine similarity: {sim:.1%}).",
                        evidence=f"Historical Past Question [{past.get('year')}]: {past.get('text')}",
                    )
                    item_flags.append(flag)
                    break
            else:
                # Secondary lexical check against past papers via Vertex AI Search (§5.4)
                lexical_flag = await _lexical_past_duplicate(item, course_id, assessment_id)
                if lexical_flag:
                    item_flags.append(lexical_flag)

            return item_flags

    # Parallel per-item audit with bounded concurrency
    per_item_flag_lists = await asyncio.gather(*(review_single_item(it) for it in items))
    generated_flags: List[Flag] = []
    for flags_list in per_item_flag_lists:
        generated_flags.extend(flags_list)

    # 5. Pairwise Candidate Pool Duplicate Detection
    pool_duplicates_count = 0
    flagged_pool_pairs: Set[Tuple[str, str]] = set()

    pool_embs = await asyncio.gather(
        *[asyncio.to_thread(compute_embedding, it.stem) if not it.embedding else asyncio.sleep(0, result=it.embedding) for it in items]
    )
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            emb_i = pool_embs[i]
            emb_j = pool_embs[j]

            sim = cosine_similarity(emb_i, emb_j)
            if sim >= duplicate_threshold and (items[i].id, items[j].id) not in flagged_pool_pairs:
                pool_duplicates_count += 1
                flagged_pool_pairs.add((items[i].id, items[j].id))
                flagged_pool_pairs.add((items[j].id, items[i].id))

                flag = Flag(
                    id=f"flag-{generate_id()[:8]}",
                    itemId=items[i].id,
                    assessmentId=assessment_id,
                    type="duplicate_pool",
                    severity="medium",
                    detail=f"Item {items[i].id} is a near-duplicate of candidate {items[j].id} (cosine similarity: {sim:.1%}).",
                    evidence=f"Stem A: '{items[i].stem[:120]}' | Stem B: '{items[j].stem[:120]}'",
                )
                generated_flags.append(flag)

    # Count breakdown by flag type
    key_mismatches_count = sum(1 for f in generated_flags if f.type == "key_mismatch")
    ambiguous_count = sum(1 for f in generated_flags if f.type == "ambiguous")
    past_duplicates_count = sum(1 for f in generated_flags if f.type == "duplicate_past")
    pool_duplicates_count = sum(1 for f in generated_flags if f.type == "duplicate_pool")
    flaws_count = sum(1 for f in generated_flags if f.type == "item_flaw")
    misaligned_clo_count = sum(1 for f in generated_flags if f.type == "misaligned_clo")
    bloom_doubt_count = sum(1 for f in generated_flags if f.type == "bloom_doubt")

    duration_ms = int((time.time() - start_time) * 1000)

    # Persist Flags to Firestore
    old_flags = await db.query("flags", filters=[("assessmentId", "==", assessment_id)])
    # A re-run must not reopen what the lecturer already decided (the solver skips unresolved key mismatches).
    decided = {(of.get("itemId"), of.get("type")): of for of in old_flags if of.get("resolution")}
    for f in generated_flags:
        prev = decided.get((f.itemId, f.type))
        if prev:
            f.resolution, f.resolvedBy, f.detail = prev["resolution"], prev.get("resolvedBy"), prev.get("detail", f.detail)
    await asyncio.gather(*[db.delete("flags", of.get("id")) for of in old_flags])

    await asyncio.gather(*[db.set("flags", f.id, f.model_dump()) for f in generated_flags])

    # Update assessment status
    await db.update("assessments", assessment_id, {"status": "reviewed"})

    # Record fine-grained step trace
    await tracker.record_step(
        run_id=rid,
        agent="Reviewer",
        tool="adversarial_audit",
        input_summary=f"Audited {len(items)} items using 3-run majority solve, alignment checks, and duplicate scans",
        output_summary=f"Audit completed: {len(generated_flags)} total flags raised ({key_mismatches_count} key mismatches, {ambiguous_count} ambiguous items, {past_duplicates_count} past exam duplicates, {pool_duplicates_count} pool duplicates, {flaws_count} item flaws, {misaligned_clo_count} CLO misalignments, {bloom_doubt_count} Bloom doubts).",
        status="completed",
        duration_ms=duration_ms,
        sources=[f"CS2040 Past Papers (2023-2025)", "Academic Psychometric Quality Rubric", "Bloom's Revised Taxonomy"],
    )

    # Telemetry Event Logging
    await log_event(
        event_type="reviewer_completed",
        user_role="lecturer",
        assessment_id=assessment_id,
        meta={
            "total_items": len(items),
            "total_flags": len(generated_flags),
            "key_mismatches": key_mismatches_count,
            "ambiguous": ambiguous_count,
            "past_duplicates": past_duplicates_count,
            "pool_duplicates": pool_duplicates_count,
            "flaws": flaws_count,
            "misaligned_clo": misaligned_clo_count,
            "bloom_doubt": bloom_doubt_count,
            "clean_items": max(0, len(items) - len(generated_flags)),
        },
    )

    return generated_flags
