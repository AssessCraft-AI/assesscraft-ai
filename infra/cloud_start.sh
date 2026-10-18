#!/usr/bin/env bash
# ==============================================================================
# AssessCraft AI — Cloud Run Instant Re-Launch Script
# Re-launches backend and frontend from Artifact Registry images (~20s). If the source
# changed since the last build it builds fresh images first. Reconnects immediately to existing Firestore, Cloud Storage, and BigQuery data.
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
export LLM_BACKEND="${LLM_BACKEND:-openrouter}"
export ALLOWED_EMAIL_DOMAINS="${ALLOWED_EMAIL_DOMAINS:-}"
export DEFAULT_ROLE="${DEFAULT_ROLE:-}"  # empty: accounts need an admin-assigned role
export MIN_INSTANCES="${MIN_INSTANCES:-0}"
# Hard cap on scale-out: bounds the bill if traffic spikes or someone scripts requests.
export MAX_INSTANCES="${MAX_INSTANCES:-3}"

if [[ -z "${GCP_PROJECT_ID}" || "${GCP_PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: GCP_PROJECT_ID is not set. Run 'gcloud config set project <ID>' or export GCP_PROJECT_ID." >&2
  exit 1
fi

SA_EMAIL="assesscraft-backend@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
BACKEND_IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${APP_NAME}/backend:latest"
FRONTEND_IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${APP_NAME}/frontend:latest"

PROJECT_NUMBER=$(gcloud projects describe "${GCP_PROJECT_ID}" --format="value(projectNumber)")
FRONTEND_URL="${FRONTEND_URL:-https://assesscraft-web-${PROJECT_NUMBER}.${GCP_REGION}.run.app}"
WEB_HASH_URL=$(gcloud run services describe assesscraft-web --region "${GCP_REGION}" --format="value(status.url)" 2>/dev/null || echo "https://assesscraft-web-i3oymqhqoq-as.a.run.app")
CORS_JSON="[\"${FRONTEND_URL}\",\"${WEB_HASH_URL}\",\"http://localhost:3000\"]"

SECRET_ARGS=()
if [[ "${LLM_BACKEND}" == "openrouter" ]]; then
  SECRET_ARGS=(--set-secrets "LLM_API_KEY=openrouter-api-key:latest")
fi

echo "=================================================================="
echo "AssessCraft AI — Re-launching Cloud Run Compute"
echo "Project : ${GCP_PROJECT_ID}"
echo "Region  : ${GCP_REGION}"
echo "Backend Image : ${BACKEND_IMAGE}"
echo "Frontend Image: ${FRONTEND_IMAGE}"
echo "=================================================================="

source infra/lib.sh
BACKEND_REPO="${BACKEND_IMAGE%:latest}"
FRONTEND_REPO="${FRONTEND_IMAGE%:latest}"
BACKEND_FP=$(source_fingerprint backend)

if ! image_tag_exists "${BACKEND_REPO}" "${BACKEND_FP}"; then
  echo "--> Backend code changed since the last build (${BACKEND_FP}); building and deploying fresh..."
  bash infra/deploy_backend.sh
else
  echo "--> Launching backend (assesscraft-api) from existing image ${BACKEND_FP}..."
  gcloud run deploy assesscraft-api \
    --image "${BACKEND_REPO}:${BACKEND_FP}" \
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
fi

BACKEND_URL=$(gcloud run services describe assesscraft-api --region "${GCP_REGION}" --format="value(status.url)")

FRONTEND_FP=$(frontend_fingerprint "${BACKEND_URL}|${GCP_PROJECT_ID}")
if ! image_tag_exists "${FRONTEND_REPO}" "${FRONTEND_FP}"; then
  echo "--> Frontend code changed since the last build (${FRONTEND_FP}); building and deploying fresh..."
  NEXT_PUBLIC_API_URL="${BACKEND_URL}" bash infra/deploy_frontend.sh
else
  echo "--> Launching frontend (assesscraft-web) from existing image ${FRONTEND_FP}..."
  gcloud run deploy assesscraft-web \
    --image "${FRONTEND_REPO}:${FRONTEND_FP}" \
    --region "${GCP_REGION}" \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances "${WEB_MAX_INSTANCES:-3}" \
    --cpu-boost \
    --min-instances 0 \
    --allow-unauthenticated
fi

FRONTEND_URL=$(gcloud run services describe assesscraft-web --region "${GCP_REGION}" --format="value(status.url)")

echo ""
echo "=================================================================="
echo "✓ Stack is LIVE and reconnected to existing project state!"
echo "  Frontend Web : ${FRONTEND_URL}"
echo "  Backend API  : ${BACKEND_URL}"
echo "  Health Check : ${BACKEND_URL}/health"
echo "=================================================================="
