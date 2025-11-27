#!/usr/bin/env bash
# Start a Celery worker for the aiagents project
# Usage: ./scripts/start_worker.sh

set -euo pipefail

# Allow overriding broker via env
: "${REDIS_URL:=}">

APP_MODULE=src.workers.celery_app:app

exec celery -A ${APP_MODULE} worker -Q aiagents -l info
