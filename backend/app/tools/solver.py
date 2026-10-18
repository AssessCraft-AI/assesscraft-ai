import time
import logging
from typing import List, Dict, Any, Tuple, Optional, Set
from ortools.sat.python import cp_model

from app.models import (
    Item,
    Blueprint,
    BlueprintCell,
    PaperVersion,
    EquivalenceReport,
    current_time_iso,
    generate_id,
)
from app.tools.equivalence import compute_equivalence_report

logger = logging.getLogger("assesscraft.solver")


def diagnose_infeasibility(
    eligible_items: List[Item],
    blueprint: Blueprint,
    num_versions: int = 2,
) -> str:
    """
    Returns a precise, human-readable diagnosis when problem is INFEASIBLE (§6):
    e.g. 'CLO3 × apply × MCQ needs 4 items per version × 2 versions = 8, pool has 5 accepted'
    """
    for cell in blueprint.cells:
        needed = cell.count * num_versions
        matching = sum(
            1
            for it in eligible_items
            if it.cloId == cell.cloId
            and it.topicId == cell.topicId
            and it.bloom.lower() == cell.bloom.lower()
            and it.qType.lower() == cell.qType.lower()
        )
        if matching < needed:
            return (
                f"{cell.cloId} × {cell.bloom} × {cell.qType} needs "
                f"{cell.count} items per version × {num_versions} versions = {needed}, "
                f"pool has {matching} accepted"
            )

    target_items = sum(c.count for c in blueprint.cells) * num_versions
    if len(eligible_items) < target_items:
        return (
            f"Total items needed is {target_items} ({num_versions} versions × {sum(c.count for c in blueprint.cells)}), "
            f"pool has {len(eligible_items)} accepted"
        )

    return "Candidate item pool is insufficient to satisfy multi-version constraints with zero overlap."


def assemble_paper_versions(
    items: List[Item],
    blueprint: Blueprint,
    num_versions: int = 2,
    excluded_item_ids: Optional[Set[str]] = None,
    conflicts: Optional[List[Tuple[str, str]]] = None,
    time_limit_s: int = 5,
) -> Tuple[List[PaperVersion], EquivalenceReport, str]:
    """
    Assembles multiple provably equivalent examination versions with zero item overlap
    using Google OR-Tools CP-SAT (Constraint Programming - Satisfiability) (§6).

    Mathematical Formulation:
    - Decision Variables: x[i, v] in {0, 1} indicating if item i is selected in version v.
    - Constraint 1 (Zero Overlap): sum_v x[i, v] <= 1 for all i.
    - Constraint 2 (Cell Parity): sum_{i in cell} x[i, v] == cell.count for all cells, versions.
    - Constraint 3 (Total Marks): sum_i (item.marks * x[i, v]) == targetMarks for all versions.
    - Constraint 4 (Bloom Parity): sum_{i in bloom} x[i, v] == targetBloom[b] for all versions.
    - Constraint 5 (Type Parity): sum_{i in type} x[i, v] == targetType[t] for all versions.
    - Constraint 6 (Conflict Exclusion): For pairs in conflicts, x[i, v] + x[j, v] <= 1 for each version.
    - Objective: Minimize max_v D_v - min_v D_v (marks-weighted difficulty), then maximise lecturer-confirmed items.
    """
    start_time = time.time()
    excluded = excluded_item_ids or set()

    # 1. Filter eligible candidates (must not be rejected or excluded)
    eligible_items = [it for it in items if it.id not in excluded and it.status != "rejected"]
    n_items = len(eligible_items)

    target_marks = blueprint.totals.get("targetMarks", blueprint.totals.get("totalMarks", 100))
    target_item_count = sum(c.count for c in blueprint.cells)

    if n_items < target_item_count * num_versions:
        logger.warning(
            f"Candidate pool has {n_items} items, but {target_item_count * num_versions} required for {num_versions} versions."
        )

    # Precompute blueprint target distributions
    target_bloom: Dict[str, int] = {}
    target_qtype: Dict[str, int] = {}
    target_clos: Dict[str, int] = {}

    for c in blueprint.cells:
        target_bloom[c.bloom] = target_bloom.get(c.bloom, 0) + c.count
        target_qtype[c.qType] = target_qtype.get(c.qType, 0) + c.count
        target_clos[c.cloId] = target_clos.get(c.cloId, 0) + c.count

    item_index_by_id = {it.id: idx for idx, it in enumerate(eligible_items)}

    # Try strict solve first; if infeasible, try relaxed cell matching
    for mode in ["strict_cells", "relaxed_topics"]:
        model = cp_model.CpModel()

        # Decision Variables: x[i, v]
        x = {}
        for i in range(n_items):
            for v in range(num_versions):
                x[i, v] = model.NewBoolVar(f"x_{i}_{v}")

        # Constraint 1: Zero item overlap between versions
        for i in range(n_items):
            model.Add(sum(x[i, v] for v in range(num_versions)) <= 1)

        # Constraint 2: Marks per version must equal target_marks
        for v in range(num_versions):
            model.Add(
                sum(eligible_items[i].marks * x[i, v] for i in range(n_items)) == target_marks
            )

        # Constraint 3: Total item count per version
        for v in range(num_versions):
            model.Add(sum(x[i, v] for i in range(n_items)) == target_item_count)

        # Constraint 4: Cognitive Level (Bloom) Parity
        for bloom_lvl, count_needed in target_bloom.items():
            matching_indices = [
                i for i, it in enumerate(eligible_items) if it.bloom.lower() == bloom_lvl.lower()
            ]
            for v in range(num_versions):
                model.Add(sum(x[i, v] for i in matching_indices) == count_needed)

        # Constraint 5: Question Type Parity (MCQ vs Short Answer)
        for qtype, count_needed in target_qtype.items():
            matching_indices = [
                i for i, it in enumerate(eligible_items) if it.qType.lower() == qtype.lower()
            ]
            for v in range(num_versions):
                model.Add(sum(x[i, v] for i in matching_indices) == count_needed)

        # Constraint 6: CLO Coverage Parity
        for clo_id, count_needed in target_clos.items():
            matching_indices = [
                i for i, it in enumerate(eligible_items) if it.cloId == clo_id
            ]
            for v in range(num_versions):
                model.Add(sum(x[i, v] for i in matching_indices) == count_needed)

        # Constraint 7: Cell matching (Strict vs Relaxed)
        if mode == "strict_cells":
            for cell in blueprint.cells:
                matching_indices = [
                    i
                    for i, it in enumerate(eligible_items)
                    if it.cloId == cell.cloId
                    and it.topicId == cell.topicId
                    and it.bloom.lower() == cell.bloom.lower()
                    and it.qType.lower() == cell.qType.lower()
                ]
                for v in range(num_versions):
                    model.Add(sum(x[i, v] for i in matching_indices) == cell.count)

        # Constraint 8: Conflict Exclusion (§6)
        if conflicts:
            for id1, id2 in conflicts:
                if id1 in item_index_by_id and id2 in item_index_by_id:
                    i1 = item_index_by_id[id1]
                    i2 = item_index_by_id[id2]
                    for v in range(num_versions):
                        model.Add(x[i1, v] + x[i2, v] <= 1)

        # Objective (§6): minimise the marks-weighted difficulty gap between versions,
        # D_v = sum_i difficulty_i(x10, integer) * marks_i * x[i, v].
        max_d = target_marks * 50
        version_difficulties = []
        for v in range(num_versions):
            v_diff = model.NewIntVar(0, max_d, f"v_diff_{v}")
            model.Add(
                v_diff
                == sum(
                    int(round(eligible_items[i].difficulty * 10)) * eligible_items[i].marks * x[i, v]
                    for i in range(n_items)
                )
            )
            version_difficulties.append(v_diff)

        # Max-min spread across versions (== |D_a - D_b| for two versions)
        d_max = model.NewIntVar(0, max_d, "d_max")
        d_min = model.NewIntVar(0, max_d, "d_min")
        model.AddMaxEquality(d_max, version_difficulties)
        model.AddMinEquality(d_min, version_difficulties)
        gap = model.NewIntVar(0, max_d, "diff_gap")
        model.Add(gap == d_max - d_min)

        # Tertiary objective: unweighted difficulty spread tie-breaker (§6 / equivalence report difficultySpread).
        # Ensures mean difficulty across versions is balanced when marks-weighted gap is tied.
        max_raw = target_item_count * 50
        raw_difficulties = []
        for v in range(num_versions):
            r_diff = model.NewIntVar(0, max_raw, f"r_diff_{v}")
            model.Add(
                r_diff
                == sum(
                    int(round(eligible_items[i].difficulty * 10)) * x[i, v]
                    for i in range(n_items)
                )
            )
            raw_difficulties.append(r_diff)

        r_max = model.NewIntVar(0, max_raw, "r_max")
        r_min = model.NewIntVar(0, max_raw, "r_min")
        model.AddMaxEquality(r_max, raw_difficulties)
        model.AddMinEquality(r_min, raw_difficulties)
        raw_gap = model.NewIntVar(0, max_raw, "raw_diff_gap")
        model.Add(raw_gap == r_max - r_min)

        # Secondary objective: prefer lecturer-confirmed items (difficulty or Bloom tag confirmed)
        confirmed_terms = [
            x[i, v]
            for i in range(n_items)
            if eligible_items[i].difficultySource == "lecturer" or eligible_items[i].bloomConfirmed
            for v in range(num_versions)
        ]
        confirmed_total = sum(confirmed_terms) if confirmed_terms else 0
        max_confirmed = target_item_count * num_versions
        w_confirmed = max_raw + 1
        w_gap = max_confirmed * w_confirmed + max_raw + 1
        model.Minimize(gap * w_gap - confirmed_total * w_confirmed + raw_gap)

        # Solve model
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(time_limit_s)
        solver.parameters.num_workers = 4
        solve_status = solver.Solve(model)

        if solve_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            solve_duration_ms = int((time.time() - start_time) * 1000)
            status_str = "OPTIMAL" if solve_status == cp_model.OPTIMAL else "FEASIBLE"
            logger.info(f"CP-SAT solved successfully ({status_str}) in mode '{mode}' ({solve_duration_ms}ms).")

            # Extract selected items per version
            labels = ["A", "B", "C", "D"]
            paper_versions: List[PaperVersion] = []

            for v in range(num_versions):
                v_label = labels[v] if v < len(labels) else f"V{v+1}"
                v_item_ids = [
                    eligible_items[i].id for i in range(n_items) if solver.Value(x[i, v]) == 1
                ]

                pv = PaperVersion(
                    id=f"ver-{blueprint.assessmentId}-{v_label.lower()}",
                    assessmentId=blueprint.assessmentId,
                    label=v_label,
                    itemIds=v_item_ids,
                    solverStats={
                        "status": status_str,
                        "mode": mode,
                        "durationMs": solve_duration_ms,
                        "branches": solver.NumBranches(),
                        "wallTime": solver.WallTime(),
                        "objective": solver.ObjectiveValue(),
                        "difficultyGapScaled": solver.Value(gap),
                    },
                )
                paper_versions.append(pv)

            # Delegate report computation to standalone tools/equivalence.py module (§6)
            equivalence_report = compute_equivalence_report(
                versions=paper_versions,
                items=eligible_items,
                blueprint=blueprint,
                solver_status=status_str,
                solver_mode=mode,
                solve_duration_ms=solve_duration_ms,
            )

            return paper_versions, equivalence_report, status_str

    # If both strict and relaxed attempts fail
    duration_ms = int((time.time() - start_time) * 1000)
    diagnosis = diagnose_infeasibility(eligible_items, blueprint, num_versions)
    logger.error(f"CP-SAT solver returned INFEASIBLE after {duration_ms}ms. Diagnosis: {diagnosis}")

    empty_report = compute_equivalence_report(
        versions=[],
        items=eligible_items,
        blueprint=blueprint,
        solver_status="INFEASIBLE",
        solver_mode="strict_and_relaxed",
        solve_duration_ms=duration_ms,
        diagnosis=diagnosis,
    )
    return [], empty_report, "INFEASIBLE"


# Standard alias matching prompt §6 specification
assemble_versions = assemble_paper_versions
