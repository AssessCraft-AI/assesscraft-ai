#!/usr/bin/env bash
# ==============================================================================
# AssessCraft AI — Cloud Run Pause / Terminate Compute Script
# Shuts down Cloud Run services while preserving 100% of the project state
# (Firestore DB, Cloud Storage files, BigQuery logs, Artifact Registry images).
# ==============================================================================
set -euo pipefail

export GCP_PROJECT_ID="${GCP_PROJECT_ID:-assesscraft-test-1012}"
# Cloud Run lives in assesscraft-test-1012; assesscraft-c5473 is the local project, so never deploy against it.
if [[ "${GCP_PROJECT_ID}" == "assesscraft-c5473" ]]; then
  echo "ERROR: assesscraft-c5473 is the local-only project; Cloud Run uses assesscraft-test-1012." >&2
  exit 1
fi
export GCP_REGION="${GCP_REGION:-asia-southeast1}"

if [[ -z "${GCP_PROJECT_ID}" || "${GCP_PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: GCP_PROJECT_ID is not set. Run 'gcloud config set project <ID>' or export GCP_PROJECT_ID." >&2
  exit 1
fi

echo "=================================================================="
echo "AssessCraft AI — Terminating Cloud Run Compute"
echo "Project : ${GCP_PROJECT_ID}"
echo "Region  : ${GCP_REGION}"
echo "=================================================================="

for SVC in assesscraft-api assesscraft-web; do
  if gcloud run services describe "${SVC}" --region="${GCP_REGION}" &>/dev/null; then
    echo "--> Deleting Cloud Run service: ${SVC}..."
    gcloud run services delete "${SVC}" --region="${GCP_REGION}" --quiet
    echo "    ✓ ${SVC} compute stopped."
  else
    echo "    ℹ ${SVC} is not currently running."
  fi
done

echo ""
echo "=================================================================="
echo "✓ Compute terminated. All compute billing stopped (\$0.00/hour)."
echo "------------------------------------------------------------------"
echo "PERSISTENT PROJECT STATUS PRESERVED:"
echo "  • Firestore (all courses, syllabus, assessments, blueprints, items, users)"
echo "  • Cloud Storage (all lecture notes, past exam PDFs, exports)"
echo "  • BigQuery (all telemetry events and metrics)"
echo "  • Artifact Registry (compiled Docker images ready for instant start)"
echo ""
echo "To re-launch in ~20 seconds without rebuilding anything, run:"
echo "  bash infra/cloud_start.sh"
echo "=================================================================="
