import pytest
from pydantic import ValidationError

from app.models import AssessmentCreate, CLO, Topic, TypeConfig
from app.tools.blueprint_rules import validate_blueprint, repair_blueprint
from app.tools.exporters import _sections


CLOS = [CLO(id=f"CLO{i}", text=f"Outcome {i}", bloomLevel="apply") for i in range(1, 4)]
TOPICS = [Topic(id="t1", name="Topic 1", cloIds=["CLO1", "CLO2", "CLO3"])]


def test_create_derives_totals_from_type_config():
    a = AssessmentCreate(courseId="X", request="r", typeConfig=[
        {"qType": "mcq", "count": 10, "marks": 10, "timeMins": 10},
        {"qType": "essay", "count": 1, "marks": 10, "timeMins": 20},
    ])
    assert (a.totalMarks, a.durationMins, a.qTypes) == (20, 30, ["mcq", "essay"])


def test_create_rejects_uneven_marks_and_duplicate_types():
    with pytest.raises(ValidationError, match="split evenly"):
        AssessmentCreate(courseId="X", request="r", typeConfig=[{"qType": "short_answer", "count": 3, "marks": 10}])
    with pytest.raises(ValidationError, match="only once"):
        AssessmentCreate(courseId="X", request="r", typeConfig=[
            {"qType": "mcq", "count": 1, "marks": 1}, {"qType": "mcq", "count": 1, "marks": 1},
        ])


def test_repair_rebuilds_to_requested_types():
    tc = [TypeConfig(qType="mcq", count=4, marks=4), TypeConfig(qType="essay", count=2, marks=16)]
    cells = repair_blueprint([], target_marks=20, clos=CLOS, topics=TOPICS, type_config=tc)
    ok, violations, totals = validate_blueprint(cells, target_marks=20, clos=CLOS, topics=TOPICS, type_config=tc)
    assert ok, violations
    assert totals["itemsByQType"] == {"mcq": 4, "essay": 2}
    assert all(c.marksEach == (1 if c.qType == "mcq" else 8) for c in cells)


def test_validate_flags_unpermitted_type_and_skips_clo_rule_when_too_few_questions():
    tc = [TypeConfig(qType="essay", count=1, marks=10)]
    cells = repair_blueprint([], target_marks=10, clos=CLOS, topics=TOPICS, type_config=tc)
    ok, violations, _ = validate_blueprint(cells, target_marks=10, clos=CLOS, topics=TOPICS, type_config=tc)
    assert ok, violations  # 1 question cannot cover 3 CLOs: rule skipped
    bad = cells + [cells[0].model_copy(update={"qType": "mcq"})]
    _, violations, _ = validate_blueprint(bad, target_marks=20, type_config=tc)
    assert any("not permitted" in v for v in violations)


def test_sections_number_questions_continuously():
    items = [{"qType": "essay"}, {"qType": "mcq"}, {"qType": "mcq"}, {"qType": "short_answer"}]
    assert [(qt, len(g), n) for qt, g, n in _sections(items)] == [("mcq", 2, 1), ("short_answer", 1, 3), ("essay", 1, 4)]
