"""Extract feature modules from the single-file frontend entry.

The split is mechanical and idempotent: functions are located by brace
matching, moved into module files with explicit imports, and cross-module
calls are routed through the dependency registry in modules/deps.js.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "frontend" / "assets"
APP = ASSETS / "app.js"
MODULES = ASSETS / "modules"
VERSION = "?v=20261101-9"

UI_CORE_ALL = [
    "$", "$$", "state", "icon", "hydrateIcons", "escapeHtml", "formatMarkdown",
    "api", "toast", "formatDate", "formatTime", "relativeDate", "greeting",
    "clamp", "debounce", "loadAppSettings", "openSettingsModal",
    "openSystemStatus", "openFeedbackModal", "openHealthPassport",
    "startVoiceInput", "speakText", "compressImageFile", "setChatImage",
    "setTriageImage", "closeModal", "bindModalClose", "scoreRing",
]

PLAN: dict[str, dict] = {
    "review.js": {
        "symbols": ["reviewChip", "reviewSummary"],
        "graph": False,
    },
    "insights.js": {
        "symbols": [
            "lineChart", "metricCard", "signalRow", "vitalSignalScore",
            "vitalItem", "profileItem", "chartMetricValues", "ageFromBirthDate",
            "formatCompact", "labelChinese",
        ],
        "graph": False,
    },
    "knowledge.js": {
        "symbols": [
            "renderKnowledge", "knowledgeResultList", "bindKnowledgeEvents",
            "bindKnowledgeResultEvents", "searchKnowledge",
        ],
        "graph": False,
    },
    "graph-view.js": {
        "symbols": [
            "renderGraph", "graphSearchSuggestions", "runGraphSearch",
            "showGraphNode",
        ],
        "graph": True,
    },
    "inspector.js": {
        "symbols": [
            "openGraphInspector", "inspectGraphNode", "commitInspectorHistory",
            "updateInspectorHistoryControls", "navigateInspectorHistory",
            "renderInspectorFacts",
        ],
        "graph": True,
    },
    "records.js": {
        "symbols": ["openRecordModal", "modalInput", "openProfileModal"],
        "graph": False,
    },
}

CROSS_NAMES = {
    "renderView", "renderChat", "renderHealth", "renderDashboard",
    "openConversation", "startNewChat", "openRecordModal", "openProfileModal",
    "openGraphInspector",
}


def find_functions(source: str) -> dict[str, tuple[int, int]]:
    found: dict[str, tuple[int, int]] = {}
    for match in re.finditer(r"^(?:async )?function (\w+)\(", source, re.MULTILINE):
        name = match.group(1)
        start = match.start()
        index = source.index("(", match.end() - 1)
        depth = 0
        while index < len(source):
            char = source[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        brace = source.index("{", index)
        depth = 0
        cursor = brace
        while cursor < len(source):
            char = source[cursor]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
            cursor += 1
        end = cursor + 1
        while end < len(source) and source[end] == "\n":
            end += 1
        found[name] = (start, end)
    return found


def used_names(body: str, available: list[str]) -> list[str]:
    names: list[str] = []
    for name in available:
        pattern = r"(?<![\w.$])" + re.escape(name) + r"\s*\("
        if re.search(pattern, body):
            names.append(name)
    return names


def exportify(body: str) -> str:
    return re.sub(r"^(async )?function ", lambda m: "export " + (m.group(1) or "") + "function ", body, count=1)


def main() -> None:
    source = APP.read_text(encoding="utf-8")
    functions = find_functions(source)
    owner: dict[str, str] = {}
    for filename, plan in PLAN.items():
        for symbol in plan["symbols"]:
            owner[symbol] = filename
    leaf_symbols = set(PLAN["insights.js"]["symbols"]) | set(PLAN["review.js"]["symbols"])
    missing = [symbol for plan in PLAN.values() for symbol in plan["symbols"] if symbol not in functions]
    if missing:
        raise SystemExit("Missing functions: " + ", ".join(sorted(set(missing))))

    MODULES.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.gettempdir()) / "zhiheng-app-backup.js"
    shutil.copy2(APP, backup)
    print(f"backup: {backup}")

    spans: list[tuple[int, int]] = []
    exported: dict[str, list[str]] = {}

    for filename, plan in PLAN.items():
        own = plan["symbols"]
        own_set = set(own)
        chunks = [source[functions[name][0]:functions[name][1]] for name in own]
        body = "\n".join(chunks)
        spans.extend(functions[name] for name in own)

        core_imports = used_names(body, UI_CORE_ALL)
        leaf_needed: dict[str, list[str]] = {}
        for name in sorted(leaf_symbols - own_set):
            if re.search(r"(?<![\w.$])" + name + r"\s*\(", body):
                leaf_needed.setdefault(owner[name], []).append(name)
        cross_imports = [
            name
            for name in sorted(CROSS_NAMES | (set(owner) - leaf_symbols - own_set))
            if name not in own_set
            and re.search(r"(?<![\w.$])" + name + r"\s*\(", body)
        ]
        for name in cross_imports:
            body = re.sub(r"(?<![\w.$])" + name + r"\s*\(", "deps." + name + "?.(", body)

        lines: list[str] = []
        if core_imports:
            lines.append("import { " + ", ".join(core_imports) + ' } from "../ui-core.js' + VERSION + '";')
        if plan["graph"]:
            lines.append('import { Graph3D } from "../graph3d.js' + VERSION + '";')
        for owner_file, symbols in leaf_needed.items():
            lines.append(
                "import { " + ", ".join(symbols) + ' } from "./' + owner_file + '";'
            )
        if cross_imports:
            lines.append('import { deps } from "./deps.js";')
        lines.append("")

        module_body = "\n".join(exportify(chunk) for chunk in chunks)
        for name in cross_imports:
            module_body = re.sub(
                r"(?<![\w.$])" + name + r"\s*\(", "deps." + name + "?.(", module_body
            )
        (MODULES / filename).write_text("\n".join(lines) + module_body, encoding="utf-8")
        exported[filename] = own
        print(f"{filename}: {len(own)} symbols, imports={core_imports}, deps={cross_imports}")

    for start, end in sorted(spans, reverse=True):
        source = source[:start] + source[end:]

    import_lines = ['import { installDeps } from "./modules/deps.js";']
    for filename, symbols in exported.items():
        import_lines.append(
            "import { " + ", ".join(symbols) + ' } from "./modules/' + filename + '";'
        )

    anchor = source.index('} from "./ui-core.js')
    anchor = source.index(";\n", anchor) + 2
    source = source[:anchor] + "\n".join(import_lines) + "\n" + source[anchor:]

    wiring_names = [
        "renderView", "renderChat", "renderHealth", "renderDashboard",
        "openConversation", "startNewChat", "openRecordModal", "openProfileModal",
        "openGraphInspector", "renderKnowledge", "renderGraph", "renderTriage",
        "modalInput", "knowledgeResultList", "graphSearchSuggestions",
    ]
    wiring = "\ninstallDeps({\n"
    for name in wiring_names:
        wiring += f"  {name},\n"
    wiring += "});\n\n"
    boot = source.rindex("bootstrap(")
    source = source[:boot] + wiring + source[boot:]

    APP.write_text(source, encoding="utf-8")
    print(f"app.js: {len(source)} chars after extraction")


if __name__ == "__main__":
    main()
