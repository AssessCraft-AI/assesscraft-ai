from collections import Counter
from typing import List, Dict, Any, Optional, Tuple
from app.models import BlueprintCell, CLO, Topic, TypeConfig


def validate_blueprint(
    cells: List[BlueprintCell],
    target_marks: int = 100,
    clos: List[CLO] = None,
    topics: List[Topic] = None,
    type_config: Optional[List[TypeConfig]] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Pure Python deterministic validation of assessment blueprint.
    Rules:
    1. Total marks must equal target_marks exactly.
    2. Every approved CLO must have > 0 marks allocated.
    3. Cell counts must be positive integers.
    4. Marks each must be valid for question type (e.g. MCQ >= 1, Short Answer >= 2).
    5. With type_config: only the lecturer's types, with exactly their question count and marks each.
    """
    violations: List[str] = []
    
    total_marks = 0
    total_items = 0
    marks_by_clo: Dict[str, int] = {}
    marks_by_bloom: Dict[str, int] = {}
    marks_by_topic: Dict[str, int] = {}
    marks_by_qtype: Dict[str, int] = {}
    items_by_qtype: Dict[str, int] = {}

    for cell in cells:
        if cell.count <= 0:
            violations.append(f"Cell for {cell.cloId} has non-positive count ({cell.count}).")
        if cell.marksEach <= 0:
            violations.append(f"Cell for {cell.cloId} has non-positive marksEach ({cell.marksEach}).")

        cell_marks = cell.count * cell.marksEach
        total_marks += cell_marks
        total_items += cell.count

        marks_by_clo[cell.cloId] = marks_by_clo.get(cell.cloId, 0) + cell_marks
        marks_by_bloom[cell.bloom] = marks_by_bloom.get(cell.bloom, 0) + cell_marks
        marks_by_topic[cell.topicId] = marks_by_topic.get(cell.topicId, 0) + cell_marks
        marks_by_qtype[cell.qType] = marks_by_qtype.get(cell.qType, 0) + cell_marks
        items_by_qtype[cell.qType] = items_by_qtype.get(cell.qType, 0) + cell.count

    # Rule 1: Exact Total Marks
    if total_marks != target_marks:
        diff = total_marks - target_marks
        if diff > 0:
            violations.append(f"Total marks ({total_marks}) exceeds target ({target_marks}) by {diff} marks.")
        else:
            violations.append(f"Total marks ({total_marks}) is short of target ({target_marks}) by {abs(diff)} marks.")

    # Rule 2: Every CLO covered (impossible when the lecturer asked for fewer questions than CLOs)
    if clos and total_items >= len(clos):
        for clo in clos:
            if marks_by_clo.get(clo.id, 0) <= 0:
                violations.append(f"CLO '{clo.id}' has 0 marks allocated (all course learning outcomes must be assessed).")

    # Rule 5: Lecturer's per-type question counts and marks
    if type_config:
        wanted = {t.qType: t for t in type_config}
        for qtype in items_by_qtype:
            if qtype not in wanted:
                violations.append(f"Question type '{qtype}' was not permitted for this assessment.")
        for t in type_config:
            if items_by_qtype.get(t.qType, 0) != t.count:
                violations.append(f"'{t.qType}' has {items_by_qtype.get(t.qType, 0)} questions; {t.count} requested.")
            if marks_by_qtype.get(t.qType, 0) != t.marks:
                violations.append(f"'{t.qType}' has {marks_by_qtype.get(t.qType, 0)} marks; {t.marks} requested.")
            if any(c.qType == t.qType and c.marksEach != t.marks // t.count for c in cells):
                violations.append(f"Every '{t.qType}' question must be worth {t.marks // t.count} marks.")

    totals = {
        "totalMarks": total_marks,
        "targetMarks": target_marks,
        "totalItems": total_items,
        "marksByClo": marks_by_clo,
        "marksByBloom": marks_by_bloom,
        "marksByTopic": marks_by_topic,
        "marksByQType": marks_by_qtype,
        "itemsByQType": items_by_qtype,
    }

    is_valid = len(violations) == 0
    return is_valid, violations, totals


def repair_blueprint(
    cells: List[BlueprintCell],
    target_marks: int = 100,
    clos: List[CLO] = None,
    topics: List[Topic] = None,
    type_config: Optional[List[TypeConfig]] = None,
) -> List[BlueprintCell]:
    """
    Deterministically repairs blueprint cells to satisfy:
    1. Exact target marks.
    2. Comprehensive CLO coverage.
    With type_config, rebuilds cells to the lecturer's per-type counts and marks instead.
    """
    if type_config:
        return _rebuild_for_types(cells, type_config, clos or [], topics or [])

    repaired = [cell.model_copy() for cell in cells]
    
    # Ensure all CLOs have at least one cell
    existing_clos = {c.cloId for c in repaired}
    if clos:
        for clo in clos:
            if clo.id not in existing_clos:
                # Find matching topic or fallback to t1
                tid = "t1"
                if topics:
                    for t in topics:
                        if clo.id in t.cloIds:
                            tid = t.id
                            break
                repaired.append(
                    BlueprintCell(
                        cloId=clo.id,
                        topicId=tid,
                        bloom=clo.bloomLevel or "apply",
                        qType="mcq",
                        count=1,
                        marksEach=2,
                    )
                )

    # Calculate current total
    current_total = sum(c.count * c.marksEach for c in repaired)
    delta = target_marks - current_total

    if delta != 0 and repaired:
        # Adjust counts on MCQ cells first (2 marks each)
        mcq_cells = [c for c in repaired if c.qType == "mcq" and c.marksEach == 2]
        if mcq_cells and delta % 2 == 0:
            step = 1 if delta > 0 else -1
            needed_adjustments = abs(delta) // 2
            for i in range(needed_adjustments):
                idx = i % len(mcq_cells)
                if delta > 0:
                    mcq_cells[idx].count += 1
                elif mcq_cells[idx].count > 1:
                    mcq_cells[idx].count -= 1
        else:
            # Direct adjustment on the largest cell
            largest_cell = max(repaired, key=lambda c: c.count * c.marksEach)
            # Rebalance marksEach or count
            if delta > 0:
                largest_cell.count += max(1, delta // largest_cell.marksEach)
            elif largest_cell.count > 1:
                largest_cell.count = max(1, largest_cell.count - abs(delta) // largest_cell.marksEach)

    return repaired


def _rebuild_for_types(
    cells: List[BlueprintCell],
    type_config: List[TypeConfig],
    clos: List[CLO],
    topics: List[Topic],
) -> List[BlueprintCell]:
    """Keeps the proposed (CLO, topic, Bloom) slots per type, trimmed/cycled to the requested count."""
    def topic_for(clo_id: str) -> str:
        return next((t.id for t in topics if clo_id in t.cloIds), topics[0].id if topics else "t1")

    default_slots = [(c.id, topic_for(c.id), c.bloomLevel or "apply") for c in clos] or [("CLO1", "t1", "apply")]
    slots = {
        t.qType: [(c.cloId, c.topicId, c.bloom) for c in cells if c.qType == t.qType for _ in range(c.count)]
        for t in type_config
    }
    # Uncovered CLOs go first in the largest type, so trimming keeps them.
    covered = {s[0] for lst in slots.values() for s in lst}
    largest = max(type_config, key=lambda t: t.count).qType
    slots[largest] = [s for s in default_slots if s[0] not in covered] + slots[largest]

    out: List[BlueprintCell] = []
    for t in type_config:
        pool = slots[t.qType] or default_slots
        picked = Counter(pool[i % len(pool)] for i in range(t.count))
        out += [
            BlueprintCell(cloId=clo, topicId=tid, bloom=bloom, qType=t.qType, count=n, marksEach=t.marks // t.count)
            for (clo, tid, bloom), n in picked.items()
        ]
    return out
