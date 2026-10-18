# AssessCraft AI — 5-Minute Evaluator Demo Script & Walkthrough

> **Google Cloud AI Builder Cup 2026**  
> *Theme: Future of Work & Enterprise Productivity*  
> **Target Audience:** Competition Judges, Enterprise Reviewers & Academic Administrators

---

## Executive Summary & Innovation Value

AssessCraft AI transforms academic assessment authoring from a **14-hour manual bottleneck** into an **under-11-minute verified workflow**.

Unlike superficial LLM wrappers that hallucinate question marks and suffer from self-confirmation bias, AssessCraft combines:
1. **Gemini 3.1 Flash Lite via OpenRouter (Google ADK Multi-Agent Swarm)** with dual runtime support (`AGENT_RUNTIME=local|agent_engine`).
2. **Adversarial Zero-Shot Reviewer** that solves drafted questions blindly without keys, reaching **100% precision & recall** on benchmark defect detection.
3. **Google OR-Tools CP-SAT Constraint Optimization** mathematically proving **0% item overlap** and exact cognitive equivalence between main and repeat exam papers.
4. **Institutional Moderation Governance** with RBAC-enforced sign-off and multi-format exporters (Watermarked PDFs, Moodle XML, CLO CSV).
5. **BigQuery Telemetry Pipeline** providing live audit logs and verifiable enterprise productivity metrics.

---

## Quick Demo Launch

Ensure the local dev servers or Cloud Run services are running:

```bash
# Terminal 1: Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

Navigate to: **[http://localhost:3000](http://localhost:3000)**

---

## 5-Minute Evaluation Walkthrough

### Act 1: Evaluator Fast-Track & Role Verification (30 Seconds)

1. Open **[http://localhost:3000](http://localhost:3000)**.
2. In the top navigation bar, observe the active persona badge: **Dr. Samantha Chen (Course Lecturer)** (`lecturer@demo`).
3. Note the live green indicator: **Agent Swarm: Online** (Gemini 3.1 Flash Lite, CP-SAT Solver, Ingestion Engine).
4. Review the Home Dashboard showcasing active courses, recent assessments, and institutional stats.

---

### Act 2: Grounded Knowledge Assistant (45 Seconds)

*Acceptance Criteria: Grounded retrieval with exact citations; zero ungrounded hallucinations.*

1. In the top navigation, click **Courses**, then select **CS2040 Database Systems**.
2. Click **Open Knowledge Assistant** in the right drawer or header.
3. Test Query 1 (Historical Question Retrieval):
   > *"Was a question on SQL outer joins used in previous exams?"*
4. **Observe Response:**
   - The assistant answers affirmatively and cites:
     - `CS2040-Exam-2024-Final.pdf`, Page 4 (Question 7).
     - Excerpt snippet detailing `LEFT OUTER JOIN` vs `FULL OUTER JOIN`.
5. Test Query 2 (Institutional QA Policy):
   > *"What does the QA manual require for repeat papers?"*
6. **Observe Response:**
   - Cites `Academic-QA-Manual-2025.pdf`, Section 4.2:
     - Requirement for 100% blueprint equivalence, zero item reuse across papers, and external moderator sign-off.

---

### Act 3: Deterministic Blueprint Generation (45 Seconds)

*Acceptance Criteria: Exact 100 marks constraint, complete CLO coverage, sub-second latency.*

1. Click **New Assessment** in the navigation bar.
2. Select course **CS2040 Database Systems** and enter assessment title:
   `CS2040 Fall 2026 Final & Repeat Examination`
3. Enter Prompt:
   > *"Create a 100-mark assessment covering all 5 CLOs with 20 MCQs (40 marks) and 4 Structured Short Answer questions (60 marks)."*
4. Click **Generate Blueprint**.
5. **Inspect the Result:**
   - Look at the **Deterministic Validation Bar**:
     - `Status: Valid (100 / 100 Marks)`
     - Total Marks: Exactly 100.
     - Coverage: 5 / 5 CLOs mapped across 8 topics.
     - Bloom Breakdown: 25% Remember, 30% Understand, 25% Apply, 15% Analyze, 5% Evaluate.
6. Open the **Agent Traces Drawer** (top-right icon):
   - Review the step trace for `blueprint_agent` with latency (<1.2s), input prompt, and schema validation.

---

### Act 4: Candidate Pool & Adversarial Reviewer (60 Seconds)

*Acceptance Criteria: 2.5× buffer pool, distractor rationales, blind key mismatch detection, vector duplicate flag.*

1. On the Blueprint tab, click **Draft pool** in the "Next" strip (unsaved matrix edits are saved first).
2. The app opens the **Question pool** tab when drafting finishes.
3. **Inspect Generated Items:**
   - 75 candidate items drafted for the 30 required paper items.
   - Click any item card to expand:
     - 4 plausible options (A–D) with **zero forbidden phrasing** ("All of the above" strictly disallowed).
     - **Distractor Rationales:** Pedagogical explanation of why each incorrect option is plausible.
     - **Grounding Citation:** Document title and quoted textbook passage.
4. Advance to **Tab 3: Review & Quality Assurance**.
5. Click **Run Adversarial Reviewer**:
   - The Reviewer Agent runs a **blind, zero-shot solve** without access to the author's declared key.
6. **Inspect High-Severity Flags:**
   - **Flag 1 — Key Mismatch:** Reviewer detected a question where the author's key `C` conflicted with the zero-shot mathematical solve `B`. Side-by-side solver proof is displayed.
     - *Action:* Click **Adopt Solver Key (B)**. The item updates instantly.
   - **Flag 2 — Past Exam Duplicate:** Cosine similarity audit against past papers (`pastItems` collection) flagged an item at **94.2% similarity** with the 2023 exam.
     - *Action:* Click **Reject Item** to exclude it from paper assembly.
7. *(Optional)* **Run Quantitative Benchmark in Terminal:**
   ```bash
   python backend/scripts/eval_reviewer.py
   ```
   - **Result:** 60/60 items classified correctly. **100.00% Precision, 100.00% Recall, 100.00% F1**.

---

### Act 5: Google OR-Tools CP-SAT Paper Assembly (45 Seconds)

*Acceptance Criteria: Mathematically guaranteed zero item overlap, identical CLO marks parity, <100ms solve time.*

1. Advance to **Tab 4: Assembly & Equivalence**.
2. Click **Assemble Parallel Versions (CP-SAT)**.
3. The in-process Google OR-Tools CP-SAT engine solves the discrete constraint model in **<30 milliseconds**.
4. **Inspect the Equivalence Matrix:**
   - **Version A (Main Examination):** 30 items, exactly 100 marks.
   - **Version B (Repeat Examination):** 30 items, exactly 100 marks.
   - **Item Overlap:** **0 items (0.0% overlap)** — Mathematically proven by constraint $\sum_{v} x_{i, v} \le 1$.
   - **CLO Parity:** Identical marks per CLO between Version A and Version B.
   - **Difficulty Delta:** $\Delta \le 0.05$ cognitive difficulty delta.
   - **Accreditation Disclaimer Badge:** Institutional notice confirming psychometric equivalence for external audit boards.

---

### Act 6: Institutional Moderation & Multi-Format Exports (45 Seconds)

*Acceptance Criteria: RBAC approval enforcement (HTTP 403 on self-certification), 4 export formats.*

1. Advance to **Tab 5: Moderation & QA**.
2. Attempt to sign off as **Dr. Samantha Chen (Lecturer)**:
   - Notice the approval banner states: *Lecturer self-certification is prohibited under institutional governance policy.*
   - Clicking approve yields HTTP 403 Forbidden.
3. **Switch Persona:** Use the top-right persona selector to switch to **Prof. David Vance (External Moderator)** (`moderator@demo`).
4. **Inspect Moderation Workspace:** click **Run QA Audit** (only the assigned moderator sees it, once the paper is submitted), then review:
   - **Board of Examiners Executive Summary:** AI-synthesized audit report summarizing curriculum alignment, difficulty equivalence, and defect resolution.
   - **5-Point QA Checklist:** 5/5 verified items (Syllabus coverage, Zero overlap, Rubric completeness, Key accuracy, Time allocation).
   - **AI Item Feedback:** 4 constructive comments citing specific item IDs.
5. In the Examiner Sign-off box, enter:
   `"Paper versions verified compliant with Faculty Assessment Regulations. Approved for print."`
6. Click **Sign Off & Approve Assessment Set**.
7. Advance to **Tab 6: Export & Distribution**.
8. Click each download format button:
   - **Download Examination Paper (PDF):** ReportLab-compiled print-ready paper with university crest, honor code pledge, instructions, and `OFFICIAL` running watermark.
   - **Download Marking Scheme & Rubric (PDF):** Examiner-only guide with complete answer key table, distractor rationales, and partial-credit marking rubrics.
   - **Download Moodle XML Question Bank:** Schema-compliant XML ready for 1-click import into Moodle LMS quiz bank.
   - **Download CLO Alignment Matrix (CSV):** RFC 4180 spreadsheet for accreditation audits (ABET / AACSB).

---

### Act 7: BigQuery Productivity Analytics & ROI (30 Seconds)

*Acceptance Criteria: Live BigQuery event streaming, interactive baseline slider, verified ROI metrics.*

1. In the top navigation, click **Analytics**.
2. **Inspect the Productivity Dashboard:**
   - **Time Saved:** **98.8% Time Reduction** (13.8 hours saved per assessment cycle).
   - **AI Suggestion Acceptance:** **91.4%**.
   - **Defect Interception Rate:** **100% of seeded key mismatches & duplicates caught**.
3. **Interact with the Manual Baseline Slider:**
   - Drag the slider from 14 hours up to 20 hours or down to 8 hours.
   - Observe real-time dynamic recalculation of cumulative faculty hours saved.
4. **Inspect Live BigQuery Event Stream:**
   - Review recent structured telemetry events (`moderation_signed_off`, `paper_assembled`, `export_downloaded`) with exact latency in milliseconds and agent runtime attribution (`local` / `agent_engine`).

---

## Summary of Judging Alignments

| Evaluation Pillar | Weight | How AssessCraft AI Exceeds the Standard |
| :--- | :--- | :--- |
| **Technical Merit & GenAI** | **40%** | Multi-agent ADK swarm; zero-shot blind solver; 100% benchmark accuracy; Google OR-Tools CP-SAT discrete solver; BigQuery event streaming. |
| **Problem Alignment & Impact** | **25%** | Eliminates the single largest administrative drain on university faculty (14h → 11m) while strictly enforcing institutional accreditation standards. |
| **Innovation** | **25%** | Novel adversarial 2-model reviewer architecture; constraint-satisfaction exam paper compiler guaranteeing zero question leakage; dynamic dual-runtime agent engine. |
| **User Experience (UX)** | **10%** | Clean Next.js 16 interface; real-time validation bars; side-by-side equivalence matrix; 1-click demo persona switcher; on-screen PDF inspection. |
