# shellcheck shell=bash
# Shared helpers for the deploy scripts (sourced, not executed). Run from the repo root.

# 12-char hash of the current working-tree contents of a directory (committed + uncommitted + new files,
# minus .gitignore'd ones). Any code change gives a new value, so it works as an image tag.
source_fingerprint() {
  { git ls-files -co --exclude-standard -z "$1" | sort -z | xargs -0 shasum 2>/dev/null || true; } | shasum | cut -c1-12
  # (exit status of the pipeline is shasum's, which always succeeds)
}

# True when IMAGE:TAG exists in Artifact Registry.
image_tag_exists() {
  gcloud artifacts docker images describe "$1:$2" &>/dev/null
}

# Point the fingerprint tag at what was just pushed as :latest, so cloud_start.sh knows it is current.
tag_fingerprint() {
  gcloud artifacts docker tags add "$1:latest" "$1:$2" --quiet
}

# Frontend fingerprint = source + backend URL (the URL is baked into the bundle).
# Firebase config changes need a manual rebuild via deploy_frontend.sh.
frontend_fingerprint() {
  printf '%s%s' "$(source_fingerprint frontend)" "$1" | shasum | cut -c1-12
}
