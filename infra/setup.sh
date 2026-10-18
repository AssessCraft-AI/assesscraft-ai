#!/usr/bin/env bash
# ==============================================================================
# AssessCraft AI — GCP Infrastructure Setup Script (Idempotent)
# Google Cloud AI Builder Cup 2026
# ==============================================================================
set -euo pipefail

# Project values & environment variables (defaults per spec)
export GCP_PROJECT_ID="${GCP_PROJECT_ID:-assesscraft-test-1012}"
# Cloud Run lives in assesscraft-test-1012; assesscraft-c5473 is the local project, so never deploy against it.
if [[ "${GCP_PROJECT_ID}" == "assesscraft-c5473" ]]; then
  echo "ERROR: assesscraft-c5473 is the local-only project; Cloud Run uses assesscraft-test-1012." >&2
  exit 1
fi
export GCP_REGION="${GCP_REGION:-asia-southeast1}"
export DOCAI_REGION="${DOCAI_REGION:-us}"
export VERTEX_SEARCH_LOC="${VERTEX_SEARCH_LOC:-global}"
export APP_NAME="${APP_NAME:-assesscraft}"
# Firebase Auth may live in its own project (e.g. assesscraft-c5473); defaults to the GCP project.
export FIREBASE_PROJECT_ID="${GCP_PROJECT_ID}"

echo "=================================================================="
echo "AssessCraft AI — Infrastructure Provisioning"
echo "Project ID    : ${GCP_PROJECT_ID}"
echo "Firebase      : ${FIREBASE_PROJECT_ID}"
echo "Primary Region: ${GCP_REGION}"
echo "DocAI Region  : ${DOCAI_REGION}"
echo "App Name      : ${APP_NAME}"
echo "=================================================================="

if [[ -z "${GCP_PROJECT_ID}" || "${GCP_PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: GCP_PROJECT_ID is not set. Please set it or run 'gcloud config set project <your-project-id>'." >&2
  exit 1
fi

gcloud config set project "${GCP_PROJECT_ID}"

# 1. Enable Required GCP APIs
echo "--> Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  discoveryengine.googleapis.com \
  documentai.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  identitytoolkit.googleapis.com \
  firebase.googleapis.com

# 2. Artifact Registry Docker Repository
echo "--> Creating Artifact Registry repository (${APP_NAME})..."
if ! gcloud artifacts repositories describe "${APP_NAME}" --location="${GCP_REGION}" &>/dev/null; then
  gcloud artifacts repositories create "${APP_NAME}" \
    --repository-format=docker \
    --location="${GCP_REGION}" \
    --description="Docker repository for AssessCraft AI services"
  echo "    Repository created."
else
  echo "    Repository already exists."
fi
# Every deploy pushes a ~1GB image; without a policy old ones pile up as storage charges.
POLICY_FILE=$(mktemp)
cat > "${POLICY_FILE}" <<'JSON'
[
  {"name": "keep-recent", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 3}},
  {"name": "delete-old", "action": {"type": "Delete"}, "condition": {"olderThan": "604800s"}}
]
JSON
gcloud artifacts repositories set-cleanup-policies "${APP_NAME}" \
  --location="${GCP_REGION}" --policy="${POLICY_FILE}" --no-dry-run --quiet >/dev/null
rm -f "${POLICY_FILE}"
echo "    Cleanup policy set (keep 3 newest images, delete others after 7 days)."

# 3. Firestore (Native mode)
echo "--> Checking / initializing Firestore..."
if ! gcloud firestore databases describe &>/dev/null; then
  echo "    Creating Firestore default database in ${GCP_REGION}..."
  gcloud firestore databases create --location="${GCP_REGION}" --type=firestore-native || true
else
  echo "    Firestore database already initialized."
fi

# 4. Cloud Storage Bucket
BUCKET_NAME="${GCP_PROJECT_ID}-${APP_NAME}"
echo "--> Creating Cloud Storage bucket (gs://${BUCKET_NAME})..."
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" &>/dev/null; then
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --location="${GCP_REGION}" \
    --uniform-bucket-level-access
  echo "    Bucket created."
else
  echo "    Bucket already exists."
fi
# Exports are served via 15-minute signed URLs and regenerated on demand, so old copies are dead weight.
LIFECYCLE_FILE=$(mktemp)
echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":7,"matchesPrefix":["exports/"]}}]}' > "${LIFECYCLE_FILE}"
gcloud storage buckets update "gs://${BUCKET_NAME}" --lifecycle-file="${LIFECYCLE_FILE}" >/dev/null
rm -f "${LIFECYCLE_FILE}"
echo "    Lifecycle rule set (exports/ deleted after 7 days)."

# 5. BigQuery Dataset and Events Table
echo "--> Checking / creating BigQuery dataset and events table..."
if ! bq show "${GCP_PROJECT_ID}:assesscraft" &>/dev/null; then
  bq mk --location="${GCP_REGION}" --dataset "${GCP_PROJECT_ID}:assesscraft"
  echo "    Dataset created."
else
  echo "    Dataset already exists."
fi

if ! bq show "${GCP_PROJECT_ID}:assesscraft.events" &>/dev/null; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  bq mk --table "${GCP_PROJECT_ID}:assesscraft.events" "${SCRIPT_DIR}/bigquery_schema.json"
  echo "    Table assesscraft.events created."
else
  echo "    Table assesscraft.events already exists."
fi

# 6. Service Account & IAM Roles
SA_NAME="assesscraft-backend"
SA_EMAIL="${SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
echo "--> Creating service account (${SA_EMAIL})..."

if ! gcloud iam service-accounts describe "${SA_EMAIL}" &>/dev/null; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="AssessCraft Backend Cloud Run Service Account"
  echo "    Service account created. Waiting for IAM propagation..."
  sleep 5
else
  echo "    Service account already exists."
fi

echo "--> Binding least-privilege IAM roles to ${SA_EMAIL}..."
ROLES=(
  "roles/aiplatform.user"
  "roles/datastore.user"
  "roles/storage.objectAdmin"
  "roles/discoveryengine.editor"
  "roles/documentai.apiUser"
  "roles/bigquery.dataEditor"
  "roles/bigquery.jobUser"
  "roles/secretmanager.secretAccessor"
)

for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None --quiet >/dev/null
  echo "    Granted ${ROLE}"
done

# Admin dashboard (create users, set role claims, disable accounts) calls Firebase Auth in the Firebase project,
# which may be a different project the current gcloud account cannot change: then print the command for its owner.
echo "--> Granting roles/firebaseauth.admin on Firebase project ${FIREBASE_PROJECT_ID}..."
FIREBASE_GRANT=(gcloud projects add-iam-policy-binding "${FIREBASE_PROJECT_ID}"
  --member="serviceAccount:${SA_EMAIL}" --role="roles/firebaseauth.admin" --condition=None --quiet)
if "${FIREBASE_GRANT[@]}" >/dev/null 2>&1; then
  echo "    Granted roles/firebaseauth.admin"
else
  echo "    WARNING: could not grant it (no IAM access to ${FIREBASE_PROJECT_ID}). Ask that project's owner to run:" >&2
  echo "      ${FIREBASE_GRANT[*]}" >&2
fi

echo "--> Allowing the backend to sign GCS URLs as itself (signed export downloads)..."
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" --quiet >/dev/null
echo "    Granted roles/iam.serviceAccountTokenCreator (self)"

# 7. Store the OpenRouter API key (needed for the default LLM_BACKEND=openrouter)
if [[ -n "${LLM_API_KEY:-}" ]]; then
  echo "--> Storing LLM_API_KEY in Secret Manager (openrouter-api-key)..."
  if gcloud secrets describe openrouter-api-key &>/dev/null; then
    printf '%s' "${LLM_API_KEY}" | gcloud secrets versions add openrouter-api-key --data-file=- >/dev/null
  else
    printf '%s' "${LLM_API_KEY}" | gcloud secrets create openrouter-api-key --data-file=- >/dev/null
  fi
  echo "    Secret stored."
fi

echo ""
echo "=================================================================="
echo "Infrastructure Setup Complete!"
echo "Backend Service Account: ${SA_EMAIL}"
echo "Storage Bucket         : gs://${BUCKET_NAME}"
echo "BigQuery Dataset       : ${GCP_PROJECT_ID}:assesscraft"
echo "=================================================================="

cat <<EOT

MANUAL FIREBASE STEPS (cannot be scripted; do these once in https://console.firebase.google.com):
  1. Firebase project "${FIREBASE_PROJECT_ID}": if it is the GCP project, add Firebase to it (Add project > select it).
  2. Authentication > Sign-in method: enable Email/Password and (optionally) Google.
  3. Project settings > Your apps > add a Web app; copy its config into NEXT_PUBLIC_FIREBASE_* for deploy_frontend.sh.
  4. After deploying the frontend: Authentication > Settings > Authorized domains > add the web URL's host.
  5. Create users and assign roles:
       cd backend && GCP_PROJECT_ID=${GCP_PROJECT_ID} FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID} python scripts/set_user_role.py <email> <admin|lecturer|moderator> --create --password '<pw>'
EOT
