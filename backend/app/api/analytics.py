import asyncio
from collections import defaultdict
from typing import Dict, Any
from fastapi import APIRouter, Depends
from app.models import User
from app.services.firestore import db
from app.tools.events import get_all_events
from app.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Comparison baseline only (the frontend lets the user change it); every other number is measured.
BASELINE_HOURS_PER_PAPER = 14.0

FLAG_LABELS = {
    "key_mismatch": "Key Mismatch",
    "duplicate_past": "Duplicate Past Paper",
    "duplicate_pool": "Duplicate in Pool",
    "item_flaw": "Item-Writing Flaw",
    "ambiguous": "Ambiguous Stem",
    "misaligned_clo": "Misaligned CLO",
    "bloom_doubt": "Bloom Level Doubt",
}

STAGE_LABELS = {
    "DocIntel": "Document Ingestion",
    "Blueprint": "Blueprint Generation",
    "ItemWriter": "Candidate Pool Drafting",
    "Reviewer": "Multi-pass Review",
    "Solver": "CP-SAT Assembly",
    "Moderation": "Moderation Review",
}


@router.get("/summary")
async def get_analytics_summary(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    # shortcut: full-collection reads; fine for a demo-sized dataset, switch to Firestore count()/aggregations at scale.
    assessments, versions, flags, runs = await asyncio.gather(
        db.query("assessments"), db.query("versions"), db.query("flags"), db.query("runs")
    )
    events = get_all_events()

    flag_counts = defaultdict(int)
    resolutions = defaultdict(int)
    for f in flags:
        flag_counts[f.get("type")] += 1
        if f.get("resolution"):
            resolutions[f["resolution"]] += 1
    total_resolved = sum(resolutions.values())

    stage_ms = defaultdict(list)
    run_totals_ms = []
    for r in runs:
        total = 0
        for step in r.get("steps", []):
            if step.get("durationMs"):
                stage_ms[step.get("agent")].append(step["durationMs"])
                total += step["durationMs"]
        if total:
            run_totals_ms.append(total)

    papers = len(versions)
    minutes_per_paper = round(sum(run_totals_ms) / len(run_totals_ms) / 60000, 3) if run_totals_ms else 0.0
    saved_per_paper = max(0.0, BASELINE_HOURS_PER_PAPER - minutes_per_paper / 60)

    return {
        "totalAssessments": len(assessments),
        "papersGenerated": papers,
        "baselineHoursPerPaper": BASELINE_HOURS_PER_PAPER,
        "assessCraftMinutesPerPaper": minutes_per_paper,
        "estimatedTimeSavedHours": round(saved_per_paper * papers, 1),
        "timeReductionPercent": round(saved_per_paper / BASELINE_HOURS_PER_PAPER * 100, 1) if papers else 0.0,
        "flagsDecided": total_resolved,
        "acceptanceRatePercent": round(resolutions["accepted"] / total_resolved * 100, 1) if total_resolved else 0.0,
        "flagsRaisedByType": [{"type": label, "count": flag_counts[key]} for key, label in FLAG_LABELS.items()],
        "timePerStage": [
            {"stage": label, "avgMinutes": round(sum(stage_ms[agent]) / len(stage_ms[agent]) / 60000, 3)}
            for agent, label in STAGE_LABELS.items()
            if stage_ms[agent]
        ],
        "totalLoggedEvents": len(events),
        "recentEvents": list(reversed(events[-20:])),
    }
