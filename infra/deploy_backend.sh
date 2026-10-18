#!/usr/bin/env bash
# ==============================================================================
# AssessCraft AI — Backend Cloud Run Deployment Script
# ==============================================================================
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

export GCP_PROJECT_ID="${GCP_PROJECT_ID:-assesscraft-test-1012}"
# Cloud Run lives in assesscraft-test-1012; assesscraft-c5473 is the local project, so never deploy against it.
if [[ "${GCP_PROJECT_ID}" == "assesscraft-c5473" ]]; then
  echo "ERROR: assesscraft-c5473 is the local-only project; Cloud Run uses assesscraft-test-1012." >&2
  exit 1
fi
export GCP_REGION="${GCP_REGION:-asia-southeast1}"
export APP_NAME="${APP_NAME:-assesscraft}"
export LLM_MODEL="${LLM_MODEL:-google/gemini-3.1-flash-lite}"
export REVIEWER_MODEL="${REVIEWER_MODEL:-google/gemini-3.1-flash-lite}"
export BUCKET="${BUCKET:-${GCP_PROJECT_ID}-${APP_NAME}}"
export BQ_DATASET="${BQ_DATASET:-assesscraft}"
export AGENT_RUNTIME="${AGENT_RUNTIME:-local}"
export SEARCH_DATASTORE_ID="${SEARCH_DATASTORE_ID:-}"
export DOCAI_PROCESSOR_ID="${DOCAI_PROCESSOR_ID:-}"
# Production is Firebase-only: demo auth stays OFF and STRICT_MODE makes the service refuse to start
# (and agents refuse to substitute canned content) unless Firestore and the LLM are really connected.
# LLM: "openrouter" (default; needs secret openrouter-api-key) or "vertex" (uses the service account)
export LLM_BACKEND="${LLM_BACKEND:-openrouter}"
# Optional comma-separated allow-list of verified email domains that may sign in (e.g. "uni.edu")
export ALLOWED_EMAIL_DOMAINS="${ALLOWED_EMAIL_DOMAINS:-}"
export DEFAULT_ROLE="${DEFAULT_ROLE:-}"  # empty: accounts need an admin-assigned role
export MIN_INSTANCES="${MIN_INSTANCES:-0}"
# Hard cap on scale-out: bounds the bill if traffic spikes or someone scripts requests.
export MAX_INSTANCES="${MAX_INSTANCES:-3}"

if [[ -z "${GCP_PROJECT_ID}" || "${GCP_PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: GCP_PROJECT_ID is not set." >&2
  exit 1
fi

if [[ "${LLM_BACKEND}" != "vertex" && "${LLM_BACKEND}" != "openrouter" ]]; then
  echo "ERROR: LLM_BACKEND must be 'openrouter' or 'vertex'." >&2
  exit 1
fi

PROJECT_NUMBER=$(gcloud projects describe "${GCP_PROJECT_ID}" --format="value(projectNumber)")
FRONTEND_URL="${FRONTEND_URL:-https://assesscraft-web-${PROJECT_NUMBER}.${GCP_REGION}.run.app}"
WEB_HASH_URL=$(gcloud run services describe assesscraft-web --region "${GCP_REGION}" --format="value(status.url)" 2>/dev/null || echo "https://assesscraft-web-i3oymqhqoq-as.a.run.app")
CORS_JSON="[\"${FRONTEND_URL}\",\"${WEB_HASH_URL}\",\"http://localhost:3000\"]"

SECRET_ARGS=()
if [[ "${LLM_BACKEND}" == "openrouter" ]]; then
  if ! gcloud secrets describe openrouter-api-key &>/dev/null; then
    echo "ERROR: LLM_BACKEND=openrouter but Secret Manager secret 'openrouter-api-key' does not exist." >&2
    echo "       Create it with: printf '%s' \"\$KEY\" | gcloud secrets create openrouter-api-key --data-file=-" >&2
    exit 1
  fi
  SECRET_ARGS=(--set-secrets "LLM_API_KEY=openrouter-api-key:latest")
fi

echo "--> Backend config: STRICT_MODE=true, demo auth OFF (Firebase ${GCP_PROJECT_ID}), LLM=${LLM_BACKEND}, CORS=${FRONTEND_URL}"

IMAGE_TAG="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${APP_NAME}/backend:latest"
SA_EMAIL="assesscraft-backend@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

source infra/lib.sh
BACKEND_FP=$(source_fingerprint backend)
echo "--> Building and submitting backend Docker image (source ${BACKEND_FP})..."
gcloud builds submit backend --tag "${IMAGE_TAG}"
tag_fingerprint "${IMAGE_TAG%:latest}" "${BACKEND_FP}"

echo "--> Deploying assesscraft-api to Cloud Run..."
gcloud run deploy assesscraft-api \
  --image "${IMAGE_TAG}" \
  --region "${GCP_REGION}" \
  --service-account "${SA_EMAIL}" \
  --set-env-vars "^#^GCP_PROJECT_ID=${GCP_PROJECT_ID}#GCP_REGION=${GCP_REGION}#LLM_MODEL=${LLM_MODEL}#REVIEWER_MODEL=${REVIEWER_MODEL}#BUCKET=${BUCKET}#BQ_DATASET=${BQ_DATASET}#AGENT_RUNTIME=${AGENT_RUNTIME}#SEARCH_DATASTORE_ID=${SEARCH_DATASTORE_ID}#DOCAI_PROCESSOR_ID=${DOCAI_PROCESSOR_ID}#ENABLE_DEMO_AUTH=false#STRICT_MODE=true#SEED_ON_STARTUP=false#LLM_BACKEND=${LLM_BACKEND}#FIREBASE_PROJECT_ID=${GCP_PROJECT_ID}#ALLOWED_EMAIL_DOMAINS=${ALLOWED_EMAIL_DOMAINS}#DEFAULT_ROLE=${DEFAULT_ROLE}#OFFLINE_HEURISTICS=false#CORS_ORIGINS=${CORS_JSON}" \
  ${SECRET_ARGS[@]+"${SECRET_ARGS[@]}"} \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900 \
  --min-instances "${MIN_INSTANCES}" \
  --max-instances "${MAX_INSTANCES}" \
  --cpu-boost \
  --allow-unauthenticated

BACKEND_URL=$(gcloud run services describe assesscraft-api --region "${GCP_REGION}" --format="value(status.url)")
echo "=================================================================="
echo "Backend deployed successfully!"
echo "Service URL: ${BACKEND_URL}"
echo "=================================================================="
