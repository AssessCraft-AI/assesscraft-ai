"""
Delete assessments whose module has no extracted CLOs/topics, with everything built on them.

Such papers were generated before the outcomes gate existed, so their blueprints cite invented CLOs.

Usage:
    python scripts/purge_assessments_without_clos.py           # dry run: list what would be deleted
    python scripts/purge_assessments_without_clos.py --apply   # delete

Deletes: assessments, blueprints, equivalenceReports, moderation (keyed by assessment id) and
items, flags, versions, runs, notifications (by assessmentId). Audit logs are kept, plus one
"purge_assessment_without_clos" audit entry per deleted paper.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.assessments import delete_assessment_data
from app.services.audit import log_audit
from app.services.firestore import db


async def find_targets() -> list:
    courses = {c["id"]: c for c in await db.query("courses")}
    return [
        a for a in await db.query("assessments")
        if not (courses.get(a.get("courseId")) or {}).get("clos")
        or not (courses.get(a.get("courseId")) or {}).get("topics")
    ]


async def purge(assessment: dict) -> dict:
    aid = assessment["id"]
    counts = await delete_assessment_data(aid)
    await log_audit(
        actor_uid="system",
        action="purge_assessment_without_clos",
        entity="assessments",
        entity_id=aid,
        before=assessment,
    )
    return counts


async def main(apply: bool) -> int:
    print(f"Firestore: {'CLOUD' if db.is_cloud else 'in-memory (nothing persistent)'}")
    targets = await find_targets()
    if not targets:
        print("No assessments belong to a module without CLOs/topics.")
        return 0
    for a in targets:
        print(f"- {a['id']}  course={a.get('courseId')}  status={a.get('status')}  title={a.get('title')!r}")
    if not apply:
        print(f"\nDry run: {len(targets)} assessment(s) would be deleted. Re-run with --apply to delete.")
        return 0
    for a in targets:
        print(f"Deleted {a['id']}: {await purge(a)}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Actually delete (default is a dry run)")
    sys.exit(asyncio.run(main(parser.parse_args().apply)))
