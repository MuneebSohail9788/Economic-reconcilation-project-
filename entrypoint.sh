#!/bin/sh
set -eu

if [ "${APP_ENV:-development}" = "production" ]; then
  if [ "${API_AUTH_ENABLED:-true}" = "true" ] && [ -z "${API_KEY:-}" ]; then
    echo "API_AUTH_ENABLED=true requires API_KEY" >&2
    exit 1
  fi
  if [ "${EXTRACTION_MODE:-ai}" = "ai" ] && [ -z "${AI_PROVIDER_URL:-}" ]; then
    echo "EXTRACTION_MODE=ai requires AI_PROVIDER_URL" >&2
    exit 1
  fi
  alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
