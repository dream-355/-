from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.graph import INTENT_RELATIONS, medical_graph


CASES_PATH = ROOT / "evals" / "retrieval_cases.json"
REPORT_PATH = ROOT / "evals" / "latest_report.json"
PASS_THRESHOLD = 0.85

# Facts may legitimately include these bridging relations regardless of intent.
BRIDGE_RELATIONS = {"relatedDisease", "relatedSymptom", "department"}


def evaluate_case(case: dict) -> dict:
    started = time.perf_counter()
    context = medical_graph.build_context(
        case["question"],
        age=case.get("age"),
        gender=case.get("gender", ""),
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    facts = context.get("facts", [])
    entities = context.get("entities", [])
    entity_text = " ".join(entity["name"] for entity in entities)
    fact_text = " ".join(fact["object"] for fact in facts)
    combined = entity_text + " " + fact_text

    intent_ok = context.get("intent") == case["intent"]
    topic_ok = case.get("topic", "") in combined if case.get("topic") else True
    forbidden_ok = not any(
        keyword in combined for keyword in case.get("forbidden_any", [])
    )

    allowed = set(INTENT_RELATIONS.get(case["intent"], [])) | BRIDGE_RELATIONS
    used_relations = {fact.get("relation") for fact in facts}
    relation_ok = used_relations.issubset(allowed) if used_relations else True
    off_intent = sorted(relation for relation in used_relations - allowed)

    citations_ok = all(fact.get("citation_id") for fact in facts)
    passed = intent_ok and topic_ok and forbidden_ok and relation_ok and citations_ok
    return {
        "id": case.get("id", case["question"]),
        "question": case["question"],
        "expected_intent": case["intent"],
        "actual_intent": context.get("intent"),
        "passed": passed,
        "intent_ok": intent_ok,
        "topic_ok": topic_ok,
        "forbidden_ok": forbidden_ok,
        "relation_ok": relation_ok,
        "off_intent_relations": off_intent,
        "citations_ok": citations_ok,
        "fact_count": len(facts),
        "entity_count": len(entities),
        "latency_ms": latency_ms,
    }


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    results = [evaluate_case(case) for case in cases]
    total = len(results)

    def rate(key: str) -> float:
        return round(sum(1 for item in results if item[key]) / total, 3)

    latencies = [item["latency_ms"] for item in results]
    with_evidence = sum(1 for item in results if item["fact_count"] > 0)
    latencies_sorted = sorted(latencies)
    p95_index = max(0, min(len(latencies_sorted) - 1, int(round(0.95 * len(latencies_sorted))) - 1))

    report = {
        "total_cases": total,
        "pass_rate": rate("passed"),
        "intent_accuracy": rate("intent_ok"),
        "topic_recall": rate("topic_ok"),
        "population_filter_pass_rate": rate("forbidden_ok"),
        "relation_filter_pass_rate": rate("relation_ok"),
        "citation_coverage": rate("citations_ok"),
        "evidence_availability": round(with_evidence / total, 3),
        "avg_facts": round(statistics.mean(item["fact_count"] for item in results), 2),
        "latency_ms_p50": round(statistics.median(latencies), 2),
        "latency_ms_p95": latencies_sorted[p95_index],
        "vector_index": medical_graph.stats().get("vector_index", {}),
        "failures": [item for item in results if not item["passed"]],
        "results": results,
    }

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"cases              : {total}")
    print(f"end-to-end pass    : {report['pass_rate']:.3f}")
    print(f"intent accuracy    : {report['intent_accuracy']:.3f}")
    print(f"topic recall       : {report['topic_recall']:.3f}")
    print(f"relation filtering : {report['relation_filter_pass_rate']:.3f}")
    print(f"population filter  : {report['population_filter_pass_rate']:.3f}")
    print(f"citation coverage  : {report['citation_coverage']:.3f}")
    print(f"evidence available : {report['evidence_availability']:.3f}")
    print(f"avg facts / query  : {report['avg_facts']}")
    print(f"latency p50/p95 ms : {report['latency_ms_p50']} / {report['latency_ms_p95']}")
    if report["failures"]:
        print("\nFAILED CASES")
        for item in report["failures"]:
            print(
                f"  {item['id']}: intent={item['actual_intent']} "
                f"intent_ok={item['intent_ok']} topic_ok={item['topic_ok']} "
                f"relation_ok={item['relation_ok']} off={item['off_intent_relations']} "
                f"forbidden_ok={item['forbidden_ok']} citations_ok={item['citations_ok']}"
            )
    print(f"\nreport written to {REPORT_PATH.relative_to(ROOT)}")

    if report["pass_rate"] < PASS_THRESHOLD:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
