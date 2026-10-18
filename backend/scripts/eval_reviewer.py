"""
Reviewer evaluation (Build Prompt §9): precision/recall of key_mismatch and duplicate detection.

Runs the REAL Reviewer on seed/eval_set.json: items are stripped of every ground-truth field
before being passed to the 3-run independent solve, and ground truth is used only for scoring.

Needs the LLM (LLM_API_KEY for OpenRouter, or LLM_BACKEND=vertex + GCP_PROJECT_ID). Without it the Reviewer would use its
offline heuristic, whose numbers say nothing about the model, so the script refuses to run
unless --allow-offline is given, and then labels the output as not valid for the pitch.

Usage:  python scripts/eval_reviewer.py [--allow-offline] [--limit N]
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.reviewer import audit_item_solve_3_runs  # noqa: E402
from app.config import settings  # noqa: E402
from app.models import Item, Option  # noqa: E402
from app.tools.similarity import compute_embedding, cosine_similarity, get_llm_client  # noqa: E402

GROUND_TRUTH_FIELDS = {"actual_correct_answer", "is_wrong_key", "is_duplicate", "duplicate_of"}


def to_reviewer_item(raw: dict) -> Item:
    """Builds an Item the Reviewer sees: no ground-truth fields, no rationale hints."""
    clean = {k: v for k, v in raw.items() if k not in GROUND_TRUTH_FIELDS}
    return Item(
        id=clean["id"],
        assessmentId="eval",
        stem=clean["stem"],
        options=[Option(**o) for o in clean.get("options", [])],
        key=clean["key"],
        rationale="",
        qType="mcq",
        marks=2,
        cloId=clean.get("cloId", "CLO1"),
        topicId=clean.get("topicId", "t1"),
        bloom=clean.get("bloom", "understand"),
        difficulty=clean.get("difficulty", 3),
        status="candidate",
    )


def scores(tp: int, fp: int, fn: int) -> tuple:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def report(title: str, tp: int, fp: int, fn: int, tn: int) -> None:
    precision, recall, f1 = scores(tp, fp, fn)
    print(f"\n--- {title} ---")
    print(f"True positives : {tp}\nFalse positives: {fp}\nFalse negatives: {fn}\nTrue negatives : {tn}")
    print(f"Precision      : {precision:.1%}\nRecall         : {recall:.1%}\nF1             : {f1:.1%}")


async def evaluate_key_mismatch(raw_items: list, client) -> tuple:
    sem = asyncio.Semaphore(8)

    async def run(raw: dict) -> bool:
        async with sem:
            flag = await audit_item_solve_3_runs(to_reviewer_item(raw), client, "")
            return flag is not None and flag.type == "key_mismatch"

    predictions = await asyncio.gather(*(run(r) for r in raw_items))
    tp = fp = fn = tn = 0
    for raw, flagged in zip(raw_items, predictions):
        truth = bool(raw.get("is_wrong_key"))
        if flagged and truth:
            tp += 1
        elif flagged:
            fp += 1
        elif truth:
            fn += 1
        else:
            tn += 1
    return tp, fp, fn, tn


def evaluate_duplicates(raw_items: list) -> tuple:
    embeddings = [compute_embedding(r["stem"]) for r in raw_items]
    tp = fp = fn = tn = 0
    for i in range(len(raw_items)):
        for j in range(i + 1, len(raw_items)):
            flagged = cosine_similarity(embeddings[i], embeddings[j]) >= settings.DUPLICATE_THRESHOLD
            truth = (
                raw_items[i].get("duplicate_of") == raw_items[j]["id"]
                or raw_items[j].get("duplicate_of") == raw_items[i]["id"]
            )
            if flagged and truth:
                tp += 1
            elif flagged:
                fp += 1
            elif truth:
                fn += 1
            else:
                tn += 1
    return tp, fp, fn, tn


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--allow-offline", action="store_true", help="run without the LLM (numbers NOT valid for the pitch)")
    parser.add_argument("--limit", type=int, default=None, help="only evaluate the first N items")
    args = parser.parse_args()

    client = get_llm_client()
    live = bool(client)
    if not live and not args.allow_offline:
        print("ERROR: LLM is not configured (OpenRouter: set LLM_API_KEY; or LLM_BACKEND=vertex + GCP_PROJECT_ID + credentials).")
        print("Without it the Reviewer uses an offline heuristic and the metrics would be meaningless.")
        print("Re-run with --allow-offline to exercise the pipeline anyway.")
        return 2

    path = os.path.join(os.path.dirname(__file__), "..", "seed", "eval_set.json")
    with open(path) as f:
        raw_items = json.load(f)
    if args.limit:
        raw_items = raw_items[: args.limit]

    print("=" * 66)
    print("AssessCraft AI - Reviewer evaluation")
    print("=" * 66)
    print(f"Items: {len(raw_items)} | model: {settings.REVIEWER_MODEL or settings.LLM_MODEL} | "
          f"duplicate threshold: {settings.DUPLICATE_THRESHOLD}")
    if not live:
        print("!! OFFLINE MODE: heuristic solver + local embeddings. NOT valid for the pitch. !!")

    report("Key mismatch detection (3-run independent solve)", *await evaluate_key_mismatch(raw_items, client))
    report(f"Near-duplicate detection (cosine >= {settings.DUPLICATE_THRESHOLD})", *evaluate_duplicates(raw_items))
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
