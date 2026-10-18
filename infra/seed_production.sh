#!/usr/bin/env bash
# ==============================================================================
# Loads the reference corpus (CS2040 course, syllabus, notes, past papers + embeddings)
# into the PRODUCTION Firestore. No demo users, no demo assessment, no pipeline run.
# Run once after setup.sh, from a machine with `gcloud auth application-default login`.
# ==============================================================================
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../backend"

export GCP_PROJECT_ID="${GCP_PROJECT_ID:-assesscraft-test-1012}"
# Cloud Run lives in assesscraft-test-1012; assesscraft-c5473 is the local project, so never deploy against it.
if [[ "${GCP_PROJECT_ID}" == "assesscraft-c5473" ]]; then
  echo "ERROR: assesscraft-c5473 is the local-only project; Cloud Run uses assesscraft-test-1012." >&2
  exit 1
fi
export GCP_REGION="${GCP_REGION:-asia-southeast1}"
if [[ -z "${GCP_PROJECT_ID}" || "${GCP_PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: GCP_PROJECT_ID is not set." >&2
  exit 1
fi

if [[ -d .venv ]]; then source .venv/bin/activate; fi
echo "--> Checking LLM connectivity first (embeddings need it)..."
python scripts/check_llm.py
echo "--> Seeding corpus into project ${GCP_PROJECT_ID}..."
python seed/load_seed.py --corpus-only
