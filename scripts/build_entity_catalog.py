from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import ROOT_DIR, settings
from neo4j import GraphDatabase


OUTPUT = ROOT_DIR / "backend" / "data" / "entity_catalog.jsonl"
LABELS = [
    "Disease",
    "Drug",
    "Symptom",
    "SymptomAndSign",
    "Check",
    "Department",
    "Treatment",
    "Operation",
    "Diagnosis",
    "Complication",
    "Cause",
    "Precautions",
]


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    query = """
    MATCH (n)
    WHERE any(label IN labels(n) WHERE label IN $labels)
      AND n.name IS NOT NULL AND n.name <> ''
    RETURN elementId(n) AS id, labels(n)[0] AS type, n.name AS name
    """
    with driver.session(database=settings.neo4j_database) as session:
        rows = session.run(query, labels=LABELS).data()
    deduplicated: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["type"], row["name"])
        deduplicated.setdefault(
            key,
            {"id": row["id"], "type": row["type"], "name": row["name"]},
        )
    with OUTPUT.open("w", encoding="utf-8") as target:
        for item in deduplicated.values():
            target.write(json.dumps(item, ensure_ascii=False) + "\n")
    driver.close()
    print(f"Wrote {len(deduplicated)} entities to {OUTPUT}")


if __name__ == "__main__":
    main()

