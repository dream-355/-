#!/usr/bin/env sh
set -eu

BASE_FILE="docker-compose.prod.yml"
TRIAL_FILE="docker-compose.trial.yml"

if [ ! -f "neo4j_backup/neo4j.dump" ]; then
    echo "Missing neo4j_backup/neo4j.dump" >&2
    exit 1
fi

echo "Stopping Neo4j before import..."
docker compose -f "$BASE_FILE" -f "$TRIAL_FILE" stop neo4j

echo "Loading Neo4j dump..."
docker compose -f "$BASE_FILE" -f "$TRIAL_FILE" run --rm \
    --entrypoint neo4j-admin \
    neo4j database load neo4j \
    --from-path=/backups \
    --overwrite-destination=true

echo "Starting Neo4j and app..."
docker compose -f "$BASE_FILE" -f "$TRIAL_FILE" up -d neo4j app

