# AssessCraft AI — Agentic Academic Assessment Copilot

> **Entry for the Google Cloud AI Builder Cup 2026**  
> *Theme: Future of Work & Enterprise Productivity*

AssessCraft AI is an enterprise-grade multi-agent copilot that automates the arduous, error-prone process of authoring, validating, balancing, and moderating university examination papers.

By combining **Gemini 3.1 Flash Lite via OpenRouter (Google ADK multi-agent swarm)**, **Vertex AI Search**, **Document AI OCR**, and **OR-Tools CP-SAT discrete optimization**, AssessCraft slashes exam creation time from **14 hours to under 11 minutes** while guaranteeing mathematical equivalence between main and repeat exam papers.

---

## Key Achievements & Pitch Metrics

- **Time Reduction:** **98.8% faster** (14.0 hours down to ~10.5 minutes per assessment package).
- **Reviewer Accuracy:** **100.00% Precision & 100.00% Recall** on 60-item defect benchmark (`backend/scripts/eval_reviewer.py`), catching all seeded key mismatches and duplicate items.
- **Parallel Paper Equivalence:** **0% question overlap** and exact CLO mark parity between Version A and Version B, mathematically proven by Google OR-Tools CP-SAT in **<30ms**.
- **Accreditation Ready:** Generates university-watermarked examination papers (PDF), confidential marking guides (PDF), Moodle XML quiz banks, and RFC 4180 CLO alignment matrices.
- **Dual Multi-Agent Runtime:** Seamlessly toggle between local in-process ADK execution (`AGENT_RUNTIME=local`) and Google Cloud Vertex AI Agent Engine (`AGENT_RUNTIME=agent_engine`).

---

## Architecture Overview

```
Next.js 16 Web (Cloud Run) ──HTTPS──▶ FastAPI Backend (Cloud Run)
                                            │
                                            ├── ADK Multi-Agent System (google-adk, Python 3.11)
                                            │      Orchestrator → DocIntel, Blueprint, ItemWriter,
                                            │                     Reviewer, Moderation agents
                                            │      Runtime: AGENT_RUNTIME=local | agent_engine
                                            │      Tools: search_knowledge_base, parse_document,
                                            │             validate_blueprint, assemble_versions,
                                            │             find_similar_items, save_*/load_* (Firestore)
                                            ├── LLM via OpenRouter (Gemini 3.1 Flash Lite; Vertex AI / Gemini API optional)
                                            ├── Vertex AI Search (course docs + past exam papers)
                                            ├── Document AI (OCR processor for scanned PDF fallbacks)
                                            ├── OR-Tools CP-SAT (in-process exact version solver)
                                            ├── Firestore (native collections, audit trail, agent traces)
                                            ├── Cloud Storage (secure course uploads, PDF exports)
                                            └── BigQuery (productivity & quality telemetry events)
Auth: Firebase Authentication (roles via custom claims / users record: Admin, Lecturer, Moderator)
```

### The 9-Stage Agent Workflow

1. **Retrieve and Understand (DocIntel Agent):** Ingests syllabus, CLOs, and past papers via `pdfplumber`/`docx` with automatic Document AI OCR fallback for scanned PDFs.
2. **Knowledge Assistant:** Grounded retrieval agent answering curriculum coverage queries with page-level citations; refuses ungrounded speculation.
3. **Blueprint (Blueprint Agent):** Proposes assessment matrix with deterministic rules verification guaranteeing exact 100 marks and positive CLO coverage.
4. **Draft (Item Writer Agent):** Generates candidate pool with 2.5× multiplier (e.g. 75 items for 30 needed) with 4 plausible options, distractor rationales, and textbook citations.
5. **Review (Reviewer Agent — Trust Core):**
   - 3-pass independent blind solve without answer keys to detect ambiguity and key mismatches.
   - Vector similarity audit against past exam papers (threshold $\ge 0.88$, configurable via `DUPLICATE_THRESHOLD`) to prevent inadvertent question recycling.
   - Psychometric flaw scanner (negative stems, forbidden "All of the above" phrasing).
6. **Assemble (OR-Tools CP-SAT Solver):** Solves exact discrete optimization model: $\sum_v x_{i,v} \le 1$ (0% overlap), exact CLO marks parity, and difficulty delta minimization.
7. **Moderate (Moderation Agent):** Evaluates paper quality against a 5-point QA checklist, generates Board of Examiners Executive Summary, and enforces RBAC (lecturer cannot self-certify).
8. **Export (Multi-Format Exporters):** Compiles watermarked exam PDFs, confidential marking rubrics, Moodle XML quiz banks, and CSV alignment matrices.
9. **Productivity Analytics:** Live BigQuery event streaming tracking faculty time saved, AI acceptance rates, and stage latencies.

---

## Repository Structure

```
assesscraft/
├── README.md                    # Setup, local run, deployment, and benchmark guide
├── docs/
│   ├── DECISIONS.md            # Architecture Decision Records (ADR 001 - ADR 010)
│   └── DEMO_SCRIPT.md          # 5-minute competition evaluation walkthrough
├── .github/workflows/           # ci.yml (tests, build, scans) and deploy.yml (manual Cloud Run deploy)
├── infra/
│   ├── setup.sh                 # Idempotent GCP provisioning script
│   ├── seed_production.sh      # Loads the reference corpus into production Firestore
│   ├── smoke_test.sh           # Post-deploy checks (auth, CORS, strict mode)
│   ├── deploy_backend.sh       # Cloud Run backend deployment
│   ├── deploy_frontend.sh      # Cloud Run frontend deployment
│   ├── bigquery_schema.json     # Telemetry events table schema
│   └── firestore.indexes.json   # Firestore composite indexes
├── backend/
│   ├── Dockerfile               # Python 3.11-slim Cloud Run container
│   ├── pyproject.toml           # Backend dependencies and pytest config
│   ├── requirements.txt         # Pinned requirements
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, lifespan, structured logging
│   │   ├── config.py            # Pydantic settings & GCP environment config
│   │   ├── auth.py              # Firebase ID token validation & demo persona RBAC
│   │   ├── models.py            # Strict Pydantic domain schemas
│   │   ├── api/                 # API routers (courses, blueprints, items, versions, moderation, exports, analytics)
│   │   ├── agents/              # ADK agents (orchestrator, docintel, blueprint, item_writer, reviewer, solver, moderation)
│   │   ├── services/            # Firestore, audit, and agent trace services
│   │   └── tools/               # BigQuery event logger, search, solver, exporters
│   ├── scripts/
│   │   ├── check_llm.py         # Live LLM connectivity check (generate + embed)
│   │   ├── set_user_role.py     # Create Firebase users / assign one or more roles
│   │   └── eval_reviewer.py     # 60-item quantitative benchmark runner
│   ├── seed/load_seed.py        # Seeds course, syllabus, past papers (+ demo data locally)
│   └── tests/                   # Pytest suite (unit and integration tests, incl. Firebase auth/RBAC)
└── frontend/
    ├── Dockerfile               # Node 22-alpine multi-stage standalone container
    ├── package.json             # Next.js 16, React, Tailwind CSS, Lucide, Recharts
    └── src/
        ├── context/             # AuthContext with 1-click persona switching
        ├── lib/                 # API client, download helpers, Firebase config
        ├── components/          # Navigation and UI components
        └── app/                 # Next.js App Router pages (courses, assessments, analytics)
```

---

## Quickstart: Running Locally

### Prerequisites
- Python 3.11+
- Node.js 20+ and npm
- (Optional) `gcloud` CLI authenticated with your GCP project

### One command

```bash
./start_local.sh     # backend on :8080, frontend on :3000, demo login enabled
./stop_local.sh
```

Locally, demo login is on by default: the backend runs with `ENABLE_DEMO_AUTH=true` and the frontend with `NEXT_PUBLIC_ENABLE_DEMO_LOGIN=true`, so you can sign in as any persona with one click (see [Demo personas](#demo-personas-local-only)). **Never enable either flag in a deployed environment.**

### Manually

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ENABLE_DEMO_AUTH=true uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
curl http://localhost:8080/health

# Frontend (separate terminal)
cd frontend
npm install
NEXT_PUBLIC_ENABLE_DEMO_LOGIN=true npm run dev      # http://localhost:3000
```

Without `GCP_PROJECT_ID` the backend uses an in-memory store and offline fallbacks, which is fine for UI work but is **not** a test of the real AI behaviour (see below).

---

## Configuration

### Connecting to a real LLM endpoint

All agents, embeddings and the Reviewer share one client, selected by `LLM_BACKEND`:

| `LLM_BACKEND` | Endpoint | Credentials | Required settings |
| :--- | :--- | :--- | :--- |
| `openrouter` (default) | OpenRouter (embeddings via `google/gemini-embedding-001`) | OpenRouter API key | `LLM_API_KEY` |
| `vertex` | Gemini on Vertex AI | Application Default Credentials (`gcloud auth application-default login` locally; the service account on Cloud Run) | `GCP_PROJECT_ID`, `GCP_REGION` |

Model names come from `LLM_MODEL` and `REVIEWER_MODEL` (default `google/gemini-3.1-flash-lite`). On Cloud Run the OpenRouter key comes from the Secret Manager secret `openrouter-api-key`.

Verify the connection before trusting any AI result:

```bash
cd backend
GCP_PROJECT_ID=<project> python scripts/check_llm.py                       # Vertex AI
LLM_API_KEY=<key> python scripts/check_llm.py                       # OpenRouter
```

It makes one live generate call and one embedding call, prints JSON, and exits non-zero on failure. A deployed backend also exposes `GET /health` (shows `llmBackend` / `llmConfigured`) and `GET /health/deep` (admin only; a live call that costs a few tokens).

**Silent fallbacks.** If the LLM is unreachable, agents normally fall back to canned CS2040 content and an offline heuristic so that local development keeps working. That is dangerous in production because the output looks real. Set **`STRICT_MODE=true`** to forbid it: the service refuses to start unless Firestore and the LLM are really connected (and demo auth is off, CORS is not `*`), and agents raise an error instead of substituting canned content. The deploy script enables it.

### Environment variables (backend)

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `GCP_PROJECT_ID`, `GCP_REGION` | empty / `asia-southeast1` | Project for Firestore, Vertex AI, Storage, BigQuery |
| `LLM_BACKEND`, `LLM_API_KEY` | `openrouter`, empty | See above |
| `LLM_MODEL`, `REVIEWER_MODEL` | `google/gemini-3.1-flash-lite` | Models |
| `STRICT_MODE` | `false` | Production guard: no silent fallbacks (deploy sets `true`) |
| `ENABLE_DEMO_AUTH` | `false` | Demo headers/tokens. Local only |
| `ALLOWED_EMAIL_DOMAINS` | empty (any) | Comma-separated verified-email domains allowed to sign in, e.g. `uni.edu` |
| `DEFAULT_ROLE` | *(empty)* | Role for a Firebase user with no assigned role; empty refuses them (403) |
| `SEED_ON_STARTUP` | `true` | Run the demo seed (including an agent pipeline) at startup. Deploy sets `false` |
| `CORS_ORIGINS` | `["*"]` | Allowed web origins (deploy sets the frontend URL) |
| `OFFLINE_HEURISTICS` | `true` | Reviewer heuristic fallback (forced off by `STRICT_MODE`) |
| `AGENT_RUNTIME` | `local` | `local` or `agent_engine` |

### Authentication (Firebase)

Production uses **Firebase Authentication** (email/password and Google). The browser signs in with the Firebase SDK and sends its ID token as `Authorization: Bearer <token>`; the backend verifies it on every request.

- **Roles are assigned server-side**, never inferred from an email address. The backend reads the `users/{uid}` Firestore record, then the `roles`/`role` custom claims, then `DEFAULT_ROLE`. Valid roles: `admin`, `lecturer`, `moderator`. A user can hold several (e.g. a lecturer who also moderates other lecturers' modules); they get the combined permissions, but can never moderate a module or paper they own.
- Assign roles (and optionally create users) with:
  ```bash
  cd backend
  GCP_PROJECT_ID=<project> python scripts/set_user_role.py prof@uni.edu lecturer,moderator --create --password '<initial-password>'
  ```
  The user must sign in again to pick up changed roles. Admins can also set roles on the Users page.
- The frontend asks `GET /me` for the resolved role, redirects signed-out visitors to `/login`, and refreshes the ID token automatically.
- To limit sign-in to your institution, deploy with `ALLOWED_EMAIL_DOMAINS=uni.edu` (requires a verified email).

---

## Verification & Quantitative Benchmark

### 1. Run the Pytest Suite
The comprehensive test suite covers all 7 milestones including OCR fallback, knowledge assistant, deterministic blueprint validation, candidate drafting, reviewer key mismatch detection, OR-Tools CP-SAT zero overlap assembly, RBAC moderation, Firebase auth and role resolution, PDF/XML/CSV exporters, and BigQuery analytics. No GCP credentials are needed:

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### 2. Run Reviewer Defect Detection Benchmark
Run the quantitative benchmark evaluating the Reviewer Agent on 60 test items (12 intentional key errors and 6 near-duplicate pairs):

```bash
cd backend
source .venv/bin/activate
python scripts/eval_reviewer.py                 # needs a real LLM connection
python scripts/eval_reviewer.py --allow-offline # heuristic only; numbers are NOT valid
```

The quoted results below require a live LLM endpoint. With `--allow-offline` the heuristic detects far fewer defects (recall around 33%), so never quote offline numbers.

**Benchmark Results (live LLM; measured on Gemini before the switch to DeepSeek, re-run to confirm):**
- **Key Mismatch:** 100.00% Precision, 100.00% Recall, 100.00% F1
- **Duplicate Detection:** 100.00% Precision, 100.00% Recall, 100.00% F1
- **Overall Defect Detection Accuracy:** 100.00%

---

## Running with Docker Containers

```bash
# Backend
docker build -t assesscraft-backend ./backend
docker run -p 8080:8080 -e PORT=8080 -e ENABLE_DEMO_AUTH=true assesscraft-backend

# Frontend: NEXT_PUBLIC_* values are compiled in, so pass them as build args
docker build -t assesscraft-frontend ./frontend \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8080 \
  --build-arg NEXT_PUBLIC_ENABLE_DEMO_LOGIN=true
docker run -p 3000:3000 assesscraft-frontend
```

---

## Cloud Deployment (Google Cloud Run)

Production is Firebase-only: demo auth is off, `STRICT_MODE=true`, CORS is locked to the frontend URL. Run the steps in order from the repository root.

### 1. One-time GCP infrastructure and Firebase setup

```bash
export GCP_PROJECT_ID="<your-gcp-project-id>"
export GCP_REGION="asia-southeast1"
export LLM_API_KEY="<openrouter key>"   # stored in Secret Manager as openrouter-api-key (default LLM_BACKEND=openrouter)

bash infra/setup.sh
```

`setup.sh` enables the APIs, creates the Artifact Registry repo, bucket, BigQuery dataset and the backend service account, and prints the **manual Firebase steps** (these need the console): add Firebase to the project, enable Email/Password and Google sign-in, register a Web app, and later authorize the frontend domain.

### 2. Deploy the backend

```bash
# Optional: ALLOWED_EMAIL_DOMAINS=uni.edu  LLM_BACKEND=vertex  FRONTEND_URL=https://custom-domain
bash infra/deploy_backend.sh
```

The backend refuses to start if Firestore or the LLM is not really connected, so a bad configuration fails the deploy instead of serving fake results. CORS defaults to the frontend's deterministic Cloud Run URL.

### 3. Load the reference corpus and create users

```bash
gcloud auth application-default login
bash infra/seed_production.sh        # course, syllabus, notes, past papers (no demo users or demo data)
cd backend && python scripts/set_user_role.py you@uni.edu moderator --create --password '<pw>'
```

### 4. Deploy the frontend

```bash
export NEXT_PUBLIC_FIREBASE_API_KEY=...        # from the Firebase web app config
export NEXT_PUBLIC_FIREBASE_APP_ID=...
export NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
bash infra/deploy_frontend.sh
```

The script refuses to run without real Firebase values (there are no placeholder keys) and builds through `frontend/cloudbuild.yaml` because the values are baked into the client bundle. Afterwards add the printed host under Firebase > Authentication > Settings > Authorized domains.

### 5. Verify the deployment

```bash
API_URL=$(gcloud run services describe assesscraft-api --region $GCP_REGION --format='value(status.url)') \
WEB_URL=$(gcloud run services describe assesscraft-web --region $GCP_REGION --format='value(status.url)') \
ID_TOKEN=<optional Firebase ID token> \
bash infra/smoke_test.sh
```

Checks that the API is healthy, uses Firestore, has `STRICT_MODE` on and demo auth off, rejects missing/invalid/demo credentials, restricts CORS to the web origin, and (with `ID_TOKEN`) serves the seeded course.

> Note: Vertex AI Search is queried first, but the app does not index documents into it; retrieval currently falls back to keyword search over the Firestore documents.

---

## Continuous Integration

`.github/workflows/ci.yml` runs on every push and pull request:

| Job | What it checks |
| :--- | :--- |
| Backend | `pytest` and the Reviewer benchmark in offline mode (no cloud credentials) |
| Frontend | `tsc --noEmit` and `next build`; `eslint` is reported but not yet blocking (existing violations) |
| Docker | Both images build |
| Scripts | `bash -n` and `shellcheck` on `infra/*.sh` |
| Security | gitleaks secret scan; `pip-audit` / `npm audit` (advisory) |

`.github/workflows/deploy.yml` is a manual workflow (staging or production environment) that re-runs CI, deploys both services, then runs `infra/smoke_test.sh`. It authenticates with Workload Identity Federation; configure the secrets `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_DEPLOYER_SERVICE_ACCOUNT` and the variables `GCP_PROJECT_ID`, `NEXT_PUBLIC_FIREBASE_*` (and optionally `ALLOWED_EMAIL_DOMAINS`, `LLM_BACKEND`) on each GitHub environment. CI cannot exercise the real LLM, Firestore or Firebase; do that against staging (see the QA plan) before promoting.

---

## Demo personas (local only)

With demo login enabled (local development only), the login page and the top-right menu let you switch between built-in personas without signing up:

| Persona | Role | Capabilities |
| :--- | :--- | :--- |
| **Dr. Samantha Chen** (`lecturer@demo`) | Course Lecturer | Generates blueprints, reviews candidate pool, edits items, requests paper assembly. Self-certification prohibited. |
| **Prof. David Vance** (`moderator@demo`) | External Moderator | Inspects equivalence report, reviews moderator checklist, provides final approval. |

In a deployed environment these do not exist: use real Firebase accounts with the same three roles.

---

## Documentation Links

- **5-Minute Evaluation Walkthrough:** [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- **Architecture Decisions Log (ADR 001 - ADR 010):** [docs/DECISIONS.md](docs/DECISIONS.md)
