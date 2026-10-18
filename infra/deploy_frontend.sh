#!/usr/bin/env bash
# ==============================================================================
# AssessCraft AI — Frontend Cloud Run Deployment Script
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
# Must match the backend's FIREBASE_PROJECT_ID, or every ID token fails the backend's audience check.
export FIREBASE_PROJECT_ID="${GCP_PROJECT_ID}"

if [[ -z "${GCP_PROJECT_ID}" || "${GCP_PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: GCP_PROJECT_ID is not set." >&2
  exit 1
fi

IMAGE_TAG="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${APP_NAME}/frontend:latest"

# Firebase web-app config (Firebase console > Project settings > Your apps). No placeholders: real sign-in needs real values.
# Unset NEXT_PUBLIC_FIREBASE_* fall back to frontend/.env.cloud (the Cloud Run project's web config), then
# frontend/.env.local (its API URL is ignored: that one points at localhost), but only from a file for this
# Firebase project: .env.local holds the local one (assesscraft-c5473).
for env_file in frontend/.env.cloud frontend/.env.local; do
  [[ -f "${env_file}" ]] || continue
  FILE_FB_PROJECT=$(grep -E '^NEXT_PUBLIC_FIREBASE_PROJECT_ID=' "${env_file}" | cut -d= -f2- || true)
  if [[ "${FILE_FB_PROJECT}" == "${FIREBASE_PROJECT_ID}" ]]; then
    while IFS='=' read -r key value; do
      if [[ "${key}" == NEXT_PUBLIC_FIREBASE_* && -z "${!key:-}" ]]; then export "${key}=${value}"; fi
    done < "${env_file}"
  else
    echo "--> Ignoring ${env_file}: its Firebase project (${FILE_FB_PROJECT:-none}) is not ${FIREBASE_PROJECT_ID}."
  fi
done
if [[ -n "${NEXT_PUBLIC_FIREBASE_PROJECT_ID:-}" && "${NEXT_PUBLIC_FIREBASE_PROJECT_ID}" != "${FIREBASE_PROJECT_ID}" ]]; then
  echo "ERROR: NEXT_PUBLIC_FIREBASE_PROJECT_ID=${NEXT_PUBLIC_FIREBASE_PROJECT_ID} but the backend uses ${FIREBASE_PROJECT_ID}; sign-in would fail." >&2
  exit 1
fi
for var in NEXT_PUBLIC_FIREBASE_API_KEY NEXT_PUBLIC_FIREBASE_APP_ID; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: ${var} is required (copy it from the Firebase web app config)." >&2
    exit 1
  fi
done

if [[ -z "${NEXT_PUBLIC_API_URL:-}" ]]; then
  NEXT_PUBLIC_API_URL=$(gcloud run services describe assesscraft-api --region "${GCP_REGION}" --format="value(status.url)" 2>/dev/null || echo "")
fi
if [[ -z "${NEXT_PUBLIC_API_URL}" ]]; then
  echo "ERROR: backend URL unknown. Deploy the backend first or set NEXT_PUBLIC_API_URL." >&2
  exit 1
fi

source infra/lib.sh
FRONTEND_FP=$(frontend_fingerprint "${NEXT_PUBLIC_API_URL}|${FIREBASE_PROJECT_ID}")

# NEXT_PUBLIC_* values are compiled into the client bundle, so they are Cloud Build args, not Cloud Run env vars.
echo "--> Building frontend image (Firebase + API URL baked in)..."
gcloud builds submit frontend --config frontend/cloudbuild.yaml --substitutions="\
_IMAGE=${IMAGE_TAG},\
_API_URL=${NEXT_PUBLIC_API_URL},\
_FB_API_KEY=${NEXT_PUBLIC_FIREBASE_API_KEY},\
_FB_AUTH_DOMAIN=${NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN:-${FIREBASE_PROJECT_ID}.firebaseapp.com},\
_FB_PROJECT_ID=${NEXT_PUBLIC_FIREBASE_PROJECT_ID:-${FIREBASE_PROJECT_ID}},\
_FB_STORAGE_BUCKET=${NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET:-${FIREBASE_PROJECT_ID}.firebasestorage.app},\
_FB_SENDER_ID=${NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID:-},\
_FB_APP_ID=${NEXT_PUBLIC_FIREBASE_APP_ID}"

tag_fingerprint "${IMAGE_TAG%:latest}" "${FRONTEND_FP}"

echo "--> Deploying assesscraft-web to Cloud Run..."
gcloud run deploy assesscraft-web \
  --image "${IMAGE_TAG}" \
  --region "${GCP_REGION}" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances "${WEB_MAX_INSTANCES:-3}" \
  --cpu-boost \
  --min-instances 0 \
  --allow-unauthenticated

FRONTEND_URL=$(gcloud run services describe assesscraft-web --region "${GCP_REGION}" --format="value(status.url)")
echo "=================================================================="
echo "Frontend deployed successfully!"
echo "Service URL: ${FRONTEND_URL}"
echo ""
echo "NEXT STEPS:"
echo "  1. Firebase console > Authentication > Settings > Authorized domains: add ${FRONTEND_URL#https://}"
echo "  2. The backend CORS allow-list must equal ${FRONTEND_URL}; if it differs, redeploy the backend with FRONTEND_URL=${FRONTEND_URL}"
echo "=================================================================="
