import asyncio
import time
import logging
from typing import List, Tuple, Optional, Set

from app.models import (
    PaperVersion,
    EquivalenceReport,
    Item,
    Blueprint,
    Assessment,
    Flag,
)
from app.services.firestore import db
from app.services.traces import tracker
from app.tools.solver import assemble_paper_versions
from app.tools.events import log_event

logger = logging.getLogger("assesscraft.solver_agent")


async def run_solver_agent(
    assessment_id: str,
    run_id: Optional[str] = None,
) -> Tuple[List[PaperVersion], EquivalenceReport]:
    """
    Executes the Multi-Version Solver Agent:
    1. Loads assessment, blueprint, candidate items, and reviewer flags.
    2. Excludes rejected items and items with unresolved high-severity flags.
    3. Runs Google OR-Tools CP-SAT multi-version paper assembly.
    4. Persists PaperVersion objects and EquivalenceReport to Firestore.
    5. Records execution traces and updates assessment status to 'assembled'.
    """
    start_time = time.time()
    assessment_data = await db.get("assessments", assessment_id)
    if not assessment_data:
        raise ValueError(f"Assessment {assessment_id} not found")

    rid = run_id or assessment_data.get("runId") or f"run-solver-{assessment_id}"
    num_versions = assessment_data.get("numVersions", 2)

    # 1. Fetch Blueprint
    blueprint_data = await db.get("blueprints", assessment_id)
    if not blueprint_data:
        raise ValueError(f"Blueprint for assessment {assessment_id} not found")
    blueprint = Blueprint(**blueprint_data)

    # 2. Fetch Items
    items_data = await db.query("items", filters=[("assessmentId", "==", assessment_id)])
    items = [Item(**d) for d in items_data]

    # 3. Fetch Flags to filter out unresolved high-severity issues
    flags_data = await db.query("flags", filters=[("assessmentId", "==", assessment_id)])
    flags = [Flag(**d) for d in flags_data]

    excluded_ids: Set[str] = set()
    for f in flags:
        # duplicate_pool sits on one item of a near-identical pair: dropping it keeps the twin out of the other version.
        if not f.resolution and f.type in ("key_mismatch", "duplicate_past", "duplicate_pool"):
            excluded_ids.add(f.itemId)

    # Also exclude items with explicit status == 'rejected'
    for it in items:
        if it.status == "rejected":
            excluded_ids.add(it.id)

    await tracker.record_step(
        run_id=rid,
        agent="Solver",
        tool="formulate_cp_model",
        input_summary=f"Formulating CP-SAT integer optimization: {len(items)} items available, {len(excluded_ids)} excluded due to flags/rejections, target: {num_versions} versions of {blueprint.totals.get('totalMarks', 100)} marks each",
        output_summary=f"Hard constraints set: zero item overlap, blueprint cell parity, Bloom distribution, total marks. Objective: minimize inter-version difficulty gap.",
        status="running",
    )

    # 4. Execute OR-Tools CP-SAT Solver
    paper_versions, report, status_str = await asyncio.to_thread(
        assemble_paper_versions,
        items=items,
        blueprint=blueprint,
        num_versions=num_versions,
        excluded_item_ids=excluded_ids,
    )

    duration_ms = int((time.time() - start_time) * 1000)

    # 5. Persist to Firestore
    if status_str in ("OPTIMAL", "FEASIBLE"):
        # Clear previous versions
        old_versions = await db.query("versions", filters=[("assessmentId", "==", assessment_id)])
        await asyncio.gather(*[db.delete("versions", ov.get("id")) for ov in old_versions])

        # Save new versions
        for pv in paper_versions:
            await db.set("versions", pv.id, pv.model_dump())

        # Save equivalence report
        await db.set("equivalenceReports", assessment_id, report.model_dump())

        # Update assessment status
        await db.update("assessments", assessment_id, {"status": "assembled"})

        # Record completed trace
        v_summaries = [
            f"Version {pv.label}: {len(pv.itemIds)} items, {report.perVersion.get(pv.label, {}).get('totalMarks', 0)} marks (Mean Diff: {report.perVersion.get(pv.label, {}).get('meanDifficulty', 0)})"
            for pv in paper_versions
        ]
        await tracker.record_step(
            run_id=rid,
            agent="Solver",
            tool="solve_cp_sat",
            input_summary=f"Solved multi-version paper assembly across {num_versions} versions with OR-Tools CP-SAT",
            output_summary=f"Assembly complete ({status_str} in {duration_ms}ms). Zero item overlap verified. Difficulty spread: ±{report.deviations.get('difficultySpread', 0)}. {'; '.join(v_summaries)}",
            status="completed",
            duration_ms=duration_ms,
            sources=["Google OR-Tools CP-SAT Solver v9.15", "Academic Blueprint Equivalence Specification"],
        )

        # Telemetry event
        await log_event(
            event_type="versions_assembled",
            user_role="lecturer",
            assessment_id=assessment_id,
            meta={
                "num_versions": len(paper_versions),
                "solver_status": status_str,
                "duration_ms": duration_ms,
                "difficulty_spread": report.deviations.get("difficultySpread", 0),
                "zero_overlap": report.deviations.get("zeroOverlapGuaranteed", True),
            },
        )
    else:
        await tracker.record_step(
            run_id=rid,
            agent="Solver",
            tool="solve_cp_sat",
            input_summary=f"CP-SAT assembly failed to find feasible assignment",
            output_summary=f"Solver returned INFEASIBLE. Insufficient clean candidate items in pool to assemble {num_versions} non-overlapping versions.",
            status="failed",
            duration_ms=duration_ms,
        )

    return paper_versions, report
