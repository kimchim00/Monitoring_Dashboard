#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "frontend/node_modules" ]; then
    echo "ERROR: Frontend dependencies not installed."
    echo "Run: cd frontend && npm install"
    exit 1
fi

PIDS=()

cleanup() {
    echo ""
    echo "Stopping all services..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    echo "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting Monitoring Dashboard..."
echo ""

# Start Monitoring API
echo "Starting Monitoring API on port 8002..."
(cd backend && uvicorn main:app --reload --port 8002) &
PIDS+=($!)

sleep 2

# Start Monitoring Frontend
echo "Starting Monitoring Frontend on port 4000..."
(cd frontend && npm start) &
PIDS+=($!)

echo ""
echo "All services running."
echo ""
echo "  Monitoring API:        http://localhost:8002"
echo "  Monitoring Dashboard:  http://localhost:4000"
echo "  API Docs:              http://localhost:8002/docs"
echo ""
echo "Press Ctrl+C to stop all services."

wait
