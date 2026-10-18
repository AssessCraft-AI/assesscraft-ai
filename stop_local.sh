#!/bin/bash
# ==============================================================================
# AssessCraft AI — Local Deployment Teardown Script
# Stops FastAPI backend (port 8080) and Next.js frontend (port 3000)
# ==============================================================================

echo "Stopping AssessCraft AI local deployment..."

# Find and stop backend processes on port 8080
BACKEND_PIDS=$(lsof -ti :8080 2>/dev/null || true)
if [ -n "$BACKEND_PIDS" ]; then
    echo "Terminating backend processes (PID: $BACKEND_PIDS)..."
    kill $BACKEND_PIDS 2>/dev/null || true
    sleep 1
    kill -9 $BACKEND_PIDS 2>/dev/null || true
    echo "✅ Backend on port 8080 stopped."
else
    echo "ℹ️ Backend (port 8080) was not running."
fi

# Find and stop frontend processes on port 3000
FRONTEND_PIDS=$(lsof -ti :3000 2>/dev/null || true)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "Terminating frontend processes (PID: $FRONTEND_PIDS)..."
    kill $FRONTEND_PIDS 2>/dev/null || true
    sleep 1
    kill -9 $FRONTEND_PIDS 2>/dev/null || true
    echo "✅ Frontend on port 3000 stopped."
else
    echo "ℹ️ Frontend (port 3000) was not running."
fi

echo "All AssessCraft AI local services have been stopped."
