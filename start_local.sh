#!/bin/bash
# ==============================================================================
# AssessCraft AI — Local Deployment & Service Runner
# Starts FastAPI backend (port 8080) and Next.js frontend (port 3000)
# ==============================================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "=========================================================="
echo "  🚀 AssessCraft AI — Local Stack Launch & Health Check   "
echo "=========================================================="

# Local runs use assesscraft-c5473 from backend/.env and frontend/.env.local. Exported shell values would
# override those files and could point local at the Cloud Run project (assesscraft-test-1012), so drop them.
unset GCP_PROJECT_ID FIREBASE_PROJECT_ID GOOGLE_APPLICATION_CREDENTIALS FIREBASE_CREDENTIALS \
      NEXT_PUBLIC_FIREBASE_API_KEY NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN NEXT_PUBLIC_FIREBASE_PROJECT_ID \
      NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID NEXT_PUBLIC_FIREBASE_APP_ID

# 1. Start FastAPI Backend (port 8080)
if lsof -i :8080 > /dev/null 2>&1; then
    echo "✅ Backend is already running on http://localhost:8080"
else
    echo "⚙️ Starting FastAPI Backend on port 8080..."
    cd "$BACKEND_DIR"
    PYTHON=python3
    if [ -x ".venv/bin/python" ]; then
        PYTHON=".venv/bin/python"
    fi
    nohup "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8080 > /tmp/assesscraft_backend.log 2>&1 &
    sleep 2
    echo "✅ FastAPI Backend started! Logs at /tmp/assesscraft_backend.log"
fi

# 2. Start Next.js Frontend (port 3000)
if lsof -i :3000 > /dev/null 2>&1; then
    echo "✅ Frontend is already running on http://localhost:3000"
else
    echo "⚙️ Starting Next.js Frontend on port 3000..."
    cd "$FRONTEND_DIR"
    nohup npm run dev > /tmp/assesscraft_frontend.log 2>&1 &
    sleep 3
    echo "✅ Frontend started! Logs at /tmp/assesscraft_frontend.log"
fi

echo ""
echo "=========================================================="
echo "  🎉 AssessCraft AI is Live Locally!                      "
echo "=========================================================="
echo "  🌐 Web App:         http://localhost:3000              "
echo "  ⚡ Backend Health:   http://localhost:8080/health       "
echo "  📚 Swagger API Docs: http://localhost:8080/docs         "
echo "=========================================================="
