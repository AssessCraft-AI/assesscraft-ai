# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: the **course lecturer** authoring a university examination package (main paper + repeat paper, marking guide, LMS export) for a course they teach. Their job: go from syllabus and CLOs to a moderation-ready, CLO-balanced paper without the multi-day manual grind, while staying the accountable author.

Secondary roles (supported, not designed-first): **Moderator** (reviews and signs off; RBAC prevents lecturer self-certification). Moderators also cover the former QA oversight role.

Near-term reader: Google Cloud AI Builder Cup 2026 judges watching a ~5-minute walkthrough (`docs/DEMO_SCRIPT.md`). Real institutional rollout is future and undecided.

## Product Purpose

An agentic copilot that automates authoring, validating, balancing and moderating exam papers. A multi-agent pipeline (DocIntel → Knowledge Assistant → Blueprint → Item Writer → Reviewer → CP-SAT Assemble → Moderation → Export → Analytics) produces two equivalent paper versions plus marking guides and exports. Success: a lecturer trusts and ships the generated package with light edits; a judge understands the pipeline and its verification in one demo.

## Positioning

Not a "generate questions" LLM wrapper. The difference is verification:
- an adversarial Reviewer that blind-solves items without keys to catch ambiguity and key mismatches, plus duplicate detection against past papers;
- an exact OR-Tools CP-SAT solver that assembles Version A/B with no item overlap and CLO mark parity;
- institutional moderation with role-enforced sign-off and a full audit trail.

## Operating Context

- Academic workflow artifacts: syllabus, CLOs (course learning outcomes), past exam papers, assessment blueprint (100 marks), item pools, main/repeat versions, Board of Examiners summary.
- Outputs: watermarked exam PDF, confidential marking guide PDF, Moodle XML, CLO alignment CSV.
- Runs locally with demo personas (one-click persona switching, `ENABLE_DEMO_AUTH`) or on Cloud Run with Firebase Auth.
- Seeded demo course: CS2040 Database Systems.

## Capabilities and Constraints

- Stack in place: Next.js 16 App Router, React 19, Tailwind CSS 4, lucide-react, Recharts (`frontend/`); FastAPI + Google ADK backend (`backend/`).
- Routes: `/`, `/login`, `/courses/[code]`, `/assessments/new`, `/assessments/[id]`, `/analytics`.
- Roles: `admin`, `lecturer`, `moderator`; assigned server-side, never inferred from email.
- `STRICT_MODE` forbids silent canned fallbacks in production; UI must not present fallback content as real AI output.
- Terminology: CLO, blueprint, item, distractor, version A/B, moderation, marking guide.

## Evidence on Hand

- Reviewer benchmark script: `backend/scripts/eval_reviewer.py` (60-item seeded defect set).
- Pitch metrics (14h → ~11 min, 100% precision/recall, 0% overlap) exist in README/demo script but are **not to be shown in product UI**. Pitch-only.
- No real testimonials, institutional customers, or pilot data. Do not fabricate.

## Product Principles

1. **The lecturer stays the author.** Agents propose; the lecturer reviews, edits, and owns the result.
2. **Show the verification, not the magic.** Reviewer findings, solver guarantees, and audit trail are the product; surface them plainly.
3. **No unearned claims.** Never present fallback output or pitch metrics as product fact.
4. **Demo-legible, faculty-durable.** Optimise for a clear 5-minute walkthrough without building anything a real lecturer would find fake.
