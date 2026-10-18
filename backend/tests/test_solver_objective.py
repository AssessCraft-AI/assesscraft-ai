"""Solver objective (Build Prompt §6): marks-weighted difficulty gap, then lecturer-confirmed items."""
from app.models import Blueprint, BlueprintCell, Item, Option
from app.tools.solver import assemble_paper_versions

OPTS = [Option(id=c, text=f"Option {c}") for c in "ABCD"]


def _mcq(item_id, difficulty, **kw):
    return Item(
        id=item_id, assessmentId="a", stem=f"MCQ {item_id}", options=OPTS, key="A", rationale="r",
        qType="mcq", marks=2, cloId="CLO1", topicId="t1", bloom="understand",
        difficulty=difficulty, status="accepted", **kw,
    )


def _short(item_id, difficulty):
    return Item(
        id=item_id, assessmentId="a", stem=f"Short {item_id}", key="k", rationale="r",
        qType="short_answer", marks=6, cloId="CLO2", topicId="t2", bloom="apply",
        difficulty=difficulty, status="accepted",
    )


def _blueprint(cells, total):
    return Blueprint(
        assessmentId="a", cells=cells,
        totals={"totalMarks": total, "targetMarks": total}, valid=True,
    )


def test_gap_is_marks_weighted_and_minimised():
    blueprint = _blueprint(
        [
            BlueprintCell(cloId="CLO1", topicId="t1", bloom="understand", qType="mcq", count=1, marksEach=2),
            BlueprintCell(cloId="CLO2", topicId="t2", bloom="apply", qType="short_answer", count=1, marksEach=6),
        ],
        total=8,
    )
    items = [_mcq("m1", 1), _mcq("m5", 5), _short("s2", 2), _short("s4", 4)]
    versions, report, status = assemble_paper_versions(items, blueprint, num_versions=2)

    assert status == "OPTIMAL"
    by_id = {i.id: i for i in items}
    scaled = [
        sum(round(by_id[i].difficulty * 10) * by_id[i].marks for i in v.itemIds) for v in versions
    ]
    gap = max(scaled) - min(scaled)
    # Best split pairs easy-MCQ with hard-short and vice versa: |26 - 22| * 10
    assert gap == 40
    assert versions[0].solverStats["difficultyGapScaled"] == gap


def test_prefers_lecturer_confirmed_items_when_difficulty_is_tied():
    blueprint = _blueprint(
        [BlueprintCell(cloId="CLO1", topicId="t1", bloom="understand", qType="mcq", count=1, marksEach=2)],
        total=2,
    )
    items = [
        _mcq("auto1", 3),
        _mcq("auto2", 3),
        _mcq("conf1", 3, difficultySource="lecturer"),
        _mcq("conf2", 3, bloomConfirmed=True),
    ]
    versions, _, status = assemble_paper_versions(items, blueprint, num_versions=2)

    assert status in ("OPTIMAL", "FEASIBLE")
    chosen = {i for v in versions for i in v.itemIds}
    assert chosen == {"conf1", "conf2"}
