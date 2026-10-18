import math
import logging
from typing import List, Dict, Any, Optional
from app.models import (
    Item,
    Blueprint,
    PaperVersion,
    EquivalenceReport,
    current_time_iso,
)

logger = logging.getLogger("assesscraft.equivalence")

# Fixed empirical comparability disclaimer mandated by Assessment Quality Framework (§6)
EMPIRICAL_LIMITATION_NOTICE = (
    "Matching blueprints do not prove equal difficulty; empirical comparability requires student response data."
)


def compute_equivalence_report(
    versions: List[PaperVersion],
    items: List[Item],
    blueprint: Blueprint,
    solver_status: str = "OPTIMAL",
    solver_mode: str = "strict",
    solve_duration_ms: int = 0,
    diagnosis: Optional[str] = None,
) -> EquivalenceReport:
    """
    Computes rigorous academic multi-version equivalence report (§6):
    - Per version:
        * marks by CLO, Bloom's taxonomy level, topic, and question type
        * mean and standard deviation (SD) of difficulty
        * share of lecturer-confirmed tags
    - Cross-version deviations:
        * difficultySpread (max - min mean difficulty)
        * sdDifficultySpread (max - min standard deviation)
        * markDifference (spread in total marks)
        * zeroOverlapGuaranteed (pairwise intersection == 0)
    - Labels each metric Guaranteed (enforced by CP-SAT constraints) or Estimated (difficulty)
    - Fixed limitation disclaimer:
      'Matching blueprints do not prove equal difficulty; empirical comparability requires student response data.'
    """
    assessment_id = blueprint.assessmentId
    target_marks = blueprint.totals.get("targetMarks", blueprint.totals.get("totalMarks", 100))

    if not versions or solver_status == "INFEASIBLE":
        return EquivalenceReport(
            assessmentId=assessment_id,
            perVersion={},
            deviations={
                "error": diagnosis or "Candidate item pool is insufficient to satisfy multi-version constraints with zero overlap.",
                "zeroOverlapGuaranteed": False,
                "difficultySpread": 0.0,
                "markDifference": 0,
                "solverMode": solver_mode,
            },
            guaranteed=[],
            estimated=[],
            limitations=[
                EMPIRICAL_LIMITATION_NOTICE,
                "Candidate item pool requires additional approved questions to satisfy blueprint constraints.",
            ],
            solverStatus=solver_status,
            createdAt=current_time_iso(),
        )

    # Build lookup table for items
    item_map: Dict[str, Item] = {it.id: it for it in items}

    per_version_stats: Dict[str, Any] = {}

    for v in versions:
        v_items = [item_map[iid] for iid in v.itemIds if iid in item_map]
        item_count = len(v_items)
        v_total_marks = sum(it.marks for it in v_items)

        # 1. Marks breakdown by Course Learning Outcome (CLO)
        clo_breakdown: Dict[str, int] = {}
        for it in v_items:
            clo_breakdown[it.cloId] = clo_breakdown.get(it.cloId, 0) + it.marks

        # 2. Marks breakdown by Bloom's cognitive taxonomy level
        bloom_breakdown: Dict[str, int] = {}
        for it in v_items:
            bloom_breakdown[it.bloom] = bloom_breakdown.get(it.bloom, 0) + it.marks

        # 3. Marks breakdown by Topic
        topic_breakdown: Dict[str, int] = {}
        for it in v_items:
            topic_breakdown[it.topicId] = topic_breakdown.get(it.topicId, 0) + it.marks

        # 4. Marks and count breakdown by Question Type
        type_breakdown: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        for it in v_items:
            type_breakdown[it.qType] = type_breakdown.get(it.qType, 0) + it.marks
            type_counts[it.qType] = type_counts.get(it.qType, 0) + 1

        # 5. Mean and Standard Deviation (SD) of difficulty
        diff_values = [it.difficulty for it in v_items]
        if diff_values:
            mean_diff = round(sum(diff_values) / len(diff_values), 3)
            variance = sum((d - mean_diff) ** 2 for d in diff_values) / len(diff_values)
            sd_diff = round(math.sqrt(variance), 3)
        else:
            mean_diff = 0.0
            sd_diff = 0.0

        # 6. Share of lecturer-confirmed tags (§6)
        confirmed_count = sum(
            1
            for it in v_items
            if it.bloomConfirmed or it.difficultySource == "lecturer" or it.status == "accepted"
        )
        lecturer_confirmed_share = round(confirmed_count / max(1, item_count), 3)

        per_version_stats[v.label] = {
            "label": v.label,
            "itemCount": item_count,
            "totalMarks": v_total_marks,
            "meanDifficulty": mean_diff,
            "sdDifficulty": sd_diff,
            "cloBreakdown": clo_breakdown,
            "bloomBreakdown": bloom_breakdown,
            "topicBreakdown": topic_breakdown,
            "typeBreakdown": type_breakdown,
            "typeCountBreakdown": type_counts,
            "lecturerConfirmedShare": lecturer_confirmed_share,
            "solveTimeMs": solve_duration_ms or v.solverStats.get("durationMs", 25),
        }

    # Cross-version deviations
    v_labels = list(per_version_stats.keys())
    mean_diffs = [per_version_stats[lbl]["meanDifficulty"] for lbl in v_labels]
    sd_diffs = [per_version_stats[lbl]["sdDifficulty"] for lbl in v_labels]
    total_marks_list = [per_version_stats[lbl]["totalMarks"] for lbl in v_labels]

    diff_spread = round(max(mean_diffs) - min(mean_diffs), 3) if mean_diffs else 0.0
    sd_spread = round(max(sd_diffs) - min(sd_diffs), 3) if sd_diffs else 0.0
    mark_diff = max(total_marks_list) - min(total_marks_list) if total_marks_list else 0

    # Verify zero item overlap
    all_sets = [set(v.itemIds) for v in versions]
    has_overlap = False
    for s1 in range(len(all_sets)):
        for s2 in range(s1 + 1, len(all_sets)):
            if all_sets[s1].intersection(all_sets[s2]):
                has_overlap = True
                break

    zero_overlap_guaranteed = not has_overlap

    # Parity checks
    clo_parity = (
        len(v_labels) > 0
        and all(per_version_stats[lbl]["cloBreakdown"] == per_version_stats[v_labels[0]]["cloBreakdown"] for lbl in v_labels)
    )
    bloom_parity = (
        len(v_labels) > 0
        and all(per_version_stats[lbl]["bloomBreakdown"] == per_version_stats[v_labels[0]]["bloomBreakdown"] for lbl in v_labels)
    )
    type_parity = (
        len(v_labels) > 0
        and all(per_version_stats[lbl]["typeBreakdown"] == per_version_stats[v_labels[0]]["typeBreakdown"] for lbl in v_labels)
    )

    deviations = {
        "difficultySpread": diff_spread,
        "sdDifficultySpread": sd_spread,
        "markDifference": mark_diff,
        "zeroOverlapGuaranteed": zero_overlap_guaranteed,
        "cloParity": clo_parity,
        "bloomParity": bloom_parity,
        "typeParity": type_parity,
        "solverMode": solver_mode,
    }

    # Metric label lists (§6 Guaranteed vs Estimated). A property is listed as
    # Guaranteed only when the assembled versions actually satisfy it.
    structural = [
        (zero_overlap_guaranteed, "Zero item overlap: no question appears in more than one version (Guaranteed)",
         "Item overlap: at least one question appears in more than one version"),
        (mark_diff == 0, f"Exact total mark parity: {target_marks} marks in every version (Guaranteed)",
         f"Total marks differ between versions by {mark_diff}"),
        (bloom_parity, "Same marks per Bloom level in every version (Guaranteed)",
         "Bloom level marks differ between versions"),
        (type_parity, "Same question format split (MCQ vs structured) in every version (Guaranteed)",
         "Question format split differs between versions"),
        (clo_parity, "Same marks per Course Learning Outcome (CLO) in every version (Guaranteed)",
         "CLO mark allocation differs between versions"),
    ]
    guaranteed = [ok_text for ok, ok_text, _ in structural if ok]
    unmet = [fail_text for ok, _, fail_text in structural if not ok]

    estimated = [
        f"Mean difficulty parity: spread within ±{diff_spread} points on a 1-5 scale (Estimated)",
        f"Difficulty standard deviation balance: spread within ±{sd_spread} (Estimated)",
        f"Cognitive load comparability index: {max(0.0, 1.0 - diff_spread / 5.0):.2%} (Estimated)",
    ]

    limitations = unmet + [
        EMPIRICAL_LIMITATION_NOTICE,
        "Item difficulty is calibrated by AI models and syllabus depth, subject to variance across different student cohorts.",
        "Psychometric calibration requires post-exam Item Response Theory (IRT) empirical student response data.",
    ]

    return EquivalenceReport(
        assessmentId=assessment_id,
        perVersion=per_version_stats,
        deviations=deviations,
        guaranteed=guaranteed,
        estimated=estimated,
        limitations=limitations,
        solverStatus=solver_status,
        createdAt=current_time_iso(),
    )
