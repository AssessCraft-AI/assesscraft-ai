#!/usr/bin/env bash
# ==============================================================================
# Post-deploy smoke test for a deployed AssessCraft environment.
#   API_URL=https://... WEB_URL=https://... bash infra/smoke_test.sh
# Optional: ID_TOKEN=<Firebase ID token> adds authenticated checks.
# Exits non-zero on the first failed check.
# ==============================================================================
set -euo pipefail

: "${API_URL:?set API_URL}"
: "${WEB_URL:?set WEB_URL}"
API_URL="${API_URL%/}"; WEB_URL="${WEB_URL%/}"
fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "ok:   $*"; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

health=$(curl -fsS "${API_URL}/health") || fail "API /health unreachable"
echo "${health}" | grep -q '"status":"healthy"' || fail "API not healthy: ${health}"
pass "API healthy"
echo "${health}" | grep -q '"datastore":"cloud_firestore"' || fail "API is not using Firestore: ${health}"
pass "Firestore connected"
echo "${health}" | grep -q '"strictMode":true' || fail "STRICT_MODE is off in this environment"
pass "STRICT_MODE on"
echo "${health}" | grep -q '"demoAuth":false' || fail "Demo auth is ON in this environment"
pass "Demo auth off"
echo "${health}" | grep -q '"llmConfigured":true' || fail "LLM is not configured"
pass "LLM configured"

[[ "$(code "${API_URL}/courses")" == "401" ]] || fail "/courses without a token must be 401"
pass "unauthenticated /courses -> 401"
[[ "$(code -H 'x-demo-role: moderator' -H 'Authorization: Bearer demo-moderator-token' "${API_URL}/courses")" == "401" ]] \
  || fail "demo credentials were accepted"
pass "demo credentials rejected"
[[ "$(code -H 'Authorization: Bearer not-a-real-token' "${API_URL}/me")" == "401" ]] || fail "garbage token must be 401"
pass "invalid token -> 401"

cors=$(curl -s -D - -o /dev/null -X OPTIONS "${API_URL}/courses" \
  -H "Origin: https://evil.example" -H "Access-Control-Request-Method: GET" | tr -d '\r' | grep -i '^access-control-allow-origin' || true)
[[ -z "${cors}" ]] || fail "CORS allows a foreign origin: ${cors}"
pass "CORS rejects foreign origin"
cors=$(curl -s -D - -o /dev/null -X OPTIONS "${API_URL}/courses" \
  -H "Origin: ${WEB_URL}" -H "Access-Control-Request-Method: GET" | tr -d '\r' | grep -i '^access-control-allow-origin' || true)
[[ "${cors}" == *"${WEB_URL}"* ]] || fail "CORS does not allow the web origin ${WEB_URL}"
pass "CORS allows the web origin"

[[ "$(code "${WEB_URL}/login")" == "200" ]] || fail "web /login not 200"
pass "web /login -> 200"

if [[ -n "${ID_TOKEN:-}" ]]; then
  auth=(-H "Authorization: Bearer ${ID_TOKEN}")
  [[ "$(code "${auth[@]}" "${API_URL}/me")" == "200" ]] || fail "/me with a valid token must be 200"
  pass "authenticated /me -> 200"
  courses=$(curl -fsS "${auth[@]}" "${API_URL}/courses")
  echo "${courses}" | grep -q 'CS2040' || fail "seed course CS2040 missing (run infra/seed_production.sh)"
  pass "seed course present"
fi
echo "All smoke checks passed."
