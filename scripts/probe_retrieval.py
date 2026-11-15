from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.graph import medical_graph


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "evals" / "probe_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    matched = 0
    for index, case in enumerate(cases, start=1):
        context = medical_graph.build_context(
            case["question"],
            age=case.get("age"),
            gender=case.get("gender", ""),
        )
        intent_ok = context["intent"] == case["intent"]
        matched += int(intent_ok)
        objects = [fact["object"] for fact in context["facts"]][:4]
        names = [entity["name"] for entity in context["entities"]][:3]
        print(
            f"{index:2d} {'OK  ' if intent_ok else 'MISS'} "
            f"expected={case['intent']:<12} got={context['intent']:<12} "
            f"facts={len(context['facts']):2d} entities={len(context['entities'])} "
            f"| entities: {' / '.join(names)[:48]} "
            f"| facts: {' / '.join(objects)[:60]}"
        )
    print(f"\nintent accuracy: {matched}/{len(cases)} = {matched / len(cases):.3f}")


if __name__ == "__main__":
    main()
