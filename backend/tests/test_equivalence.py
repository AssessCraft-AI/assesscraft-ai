import pytest
from app.models import (
    Blueprint,
    BlueprintCell,
    Item,
    Option,
    PaperVersion,
)
from app.tools.equivalence import compute_equivalence_report, EMPIRICAL_LIMITATION_NOTICE
from app.tools.solver import assemble_versions, assemble_paper_versions, diagnose_infeasibility


def create_test_blueprint_and_items(assessment_id: str = "asm-equiv-test"):
    cells = [
        BlueprintCell(cloId="CLO1", topicId="t1", bloom="understand", qType="mcq", count=2, marksEach=5),
        BlueprintCell(cloId="CLO2", topicId="t2", bloom="apply", qType="short_answer", count=1, marksEach=10),
    ]
    blueprint = Blueprint(
        assessmentId=assessment_id,
        cells=cells,
        totals={"totalMarks": 20, "targetMarks": 20, "totalItems": 3},
        valid=True,
    )

    items = []
    # 6 MCQs for CLO1 (need 2 per version * 2 versions = 4)
    for i in range(6):
        items.append(
            Item(
                id=f"mcq-{i}",
                assessmentId=assessment_id,
                stem=f"MCQ {i} testing relational modeling concepts",
                options=[Option(id="A", text="Opt A"), Option(id="B", text="Opt B")],
                key="A",
                rationale="Rationale",
                qType="mcq",
                marks=5,
                cloId="CLO1",
                topicId="t1",
                bloom="understand",
                bloomConfirmed=True,
                difficulty=2 + (i % 3),
                status="accepted",
            )
        )
    # 3 Short Answers for CLO2 (need 1 per version * 2 versions = 2)
    for i in range(3):
        items.append(
            Item(
                id=f"sa-{i}",
                assessmentId=assessment_id,
                stem=f"Short answer {i} applying SQL joins",
                key="Answer",
                rationale="Rubric",
                qType="short_answer",
                marks=10,
                cloId="CLO2",
                topicId="t2",
                bloom="apply",
                difficultySource="lecturer",
                difficulty=3 + (i % 2),
                status="accepted",
            )
        )

    return blueprint, items


def test_equivalence_report_breakdowns_and_disclaimer():
    blueprint, items = create_test_blueprint_and_items()
    versions, report, status = assemble_versions(items, blueprint, num_versions=2)

    assert status == "OPTIMAL"
    assert len(versions) == 2
    assert report.solverStatus == "OPTIMAL"

    # 1. Limitation text exact match per §6
    expected_disclaimer = "Matching blueprints do not prove equal difficulty; empirical comparability requires student response data."
    assert report.limitations[0] == expected_disclaimer
    assert EMPIRICAL_LIMITATION_NOTICE == expected_disclaimer

    # 2. Per-version breakdowns
    for v_label in ["A", "B"]:
        stats = report.perVersion[v_label]
        assert stats["totalMarks"] == 20
        assert stats["itemCount"] == 3

        # CLO breakdown: CLO1 has 2 items * 5 marks = 10, CLO2 has 1 item * 10 marks = 10
        assert stats["cloBreakdown"]["CLO1"] == 10
        assert stats["cloBreakdown"]["CLO2"] == 10

        # Bloom breakdown: understand = 10, apply = 10
        assert stats["bloomBreakdown"]["understand"] == 10
        assert stats["bloomBreakdown"]["apply"] == 10

        # Topic breakdown: t1 = 10, t2 = 10
        assert stats["topicBreakdown"]["t1"] == 10
        assert stats["topicBreakdown"]["t2"] == 10

        # Question type breakdown: mcq = 10, short_answer = 10
        assert stats["typeBreakdown"]["mcq"] == 10
        assert stats["typeBreakdown"]["short_answer"] == 10

        # Difficulty metrics
        assert stats["meanDifficulty"] > 0
        assert isinstance(stats["sdDifficulty"], float)

        # Lecturer confirmed share
        assert stats["lecturerConfirmedShare"] > 0.5

    # 3. Guaranteed vs Estimated labels per §6
    assert any("Guaranteed" in g for g in report.guaranteed)
    assert any("Zero item overlap" in g for g in report.guaranteed)
    assert any("Exact total mark parity" in g for g in report.guaranteed)

    assert any("Estimated" in e for e in report.estimated)
    assert any("Mean difficulty parity" in e for e in report.estimated)


def test_infeasible_diagnosis_diagnosis_string():
    # Only 1 short answer item provided, but 2 versions need 2 items total
    blueprint, items = create_test_blueprint_and_items()
    # Filter items to have only 1 short answer
    insufficient_items = [it for it in items if it.qType == "mcq"] + [items[-1]]

    diagnosis = diagnose_infeasibility(insufficient_items, blueprint, num_versions=2)
    assert "CLO2 × apply × short_answer needs 1 items per version × 2 versions = 2, pool has 1 accepted" in diagnosis

    versions, report, status = assemble_versions(insufficient_items, blueprint, num_versions=2)
    assert status == "INFEASIBLE"
    assert len(versions) == 0
    assert "CLO2 × apply × short_answer needs" in report.deviations["error"]
    assert report.limitations[0] == EMPIRICAL_LIMITATION_NOTICE


def test_conflict_constraint_respected():
    blueprint, items = create_test_blueprint_and_items()

    # Conflicting items mcq-0 and mcq-1 must not appear together in the same version
    conflicts = [("mcq-0", "mcq-1")]
    versions, report, status = assemble_versions(
        items, blueprint, num_versions=2, conflicts=conflicts
    )
    assert status == "OPTIMAL"

    for v in versions:
        selected = set(v.itemIds)
        assert not ({"mcq-0", "mcq-1"}.issubset(selected)), "Conflicting items mcq-0 and mcq-1 appeared in the same version!"
