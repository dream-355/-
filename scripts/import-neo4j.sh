#!/usr/bin/env sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

if [ ! -f "neo4j_backup/neo4j.dump" ]; then
    echo "Missing neo4j_backup/neo4j.dump" >&2
    exit 1
fi

echo "Stopping Neo4j before import..."
docker compose -f "$COMPOSE_FILE" stop neo4j

echo "Loading Neo4j dump..."
docker compose -f "$COMPOSE_FILE" run --rm \
    --entrypoint neo4j-admin \
    neo4j database load neo4j \
    --from-path=/backups \
    --overwrite-destination=true

echo "Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

