#!/bin/bash
# Railway automatically sets PORT env var, default to 8000 if not set
PORT_VALUE="${PORT:-8000}"
echo "Starting server on port $PORT_VALUE"
exec uvicorn server:app --host 0.0.0.0 --port "$PORT_VALUE"
