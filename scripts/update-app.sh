#!/usr/bin/env sh
set -eu

APP_DIR="${APP_DIR:-/opt/zhiheng}"
BASE_FILE="docker-compose.prod.yml"
TRIAL_FILE="docker-compose.trial.yml"

cd "$APP_DIR"

echo "Rebuilding the application container..."
docker compose -f "$BASE_FILE" -f "$TRIAL_FILE" up -d --build app

echo "Waiting for the application health check..."
sleep 5
docker compose -f "$BASE_FILE" -f "$TRIAL_FILE" ps app
docker compose -f "$BASE_FILE" -f "$TRIAL_FILE" logs --tail=40 app

