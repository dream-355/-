"""End-to-end smoke test using headless Edge and DOM assertions.

Requires the local server on 127.0.0.1:8000 and Microsoft Edge installed.
No Node.js or Playwright dependency, so it runs on the competition laptop.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

VIEWS = {
    "dashboard": ["PERSONAL HEALTH COMMAND CENTER", "hero-banner"],
    "chat": ["chat-workspace", "chat-composer"],
    "health": ["health-layout", "vitals-overview"],
    "triage": ["CLINICAL SIGNAL RECOGNITION", "triage"],
    "graph": ["main-graph-canvas", "graph-insight-panel"],
    "knowledge": ["KNOWLEDGE", "知识"],
}


def find_edge() -> str:
    for path in EDGE_CANDIDATES:
        if Path(path).exists():
            return path
    raise SystemExit("Microsoft Edge not found")


def dump_dom(edge: str, url: str, profile: Path) -> str:
    result = subprocess.run(
        [
            edge,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--disable-extensions",
            f"--user-data-dir={profile}",
            "--virtual-time-budget=15000",
            "--dump-dom",
            url,
        ],
        capture_output=True,
        timeout=120,
    )
    return result.stdout.decode("utf-8", errors="ignore")


def main() -> None:
    edge = find_edge()
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for view, markers in VIEWS.items():
            url = f"http://127.0.0.1:8000/?demo=1&view={view}"
            dom = dump_dom(edge, url, Path(tmp) / f"profile-{view}")
            missing = [marker for marker in markers if marker not in dom]
            if missing:
                failures.append(f"{view}: missing {missing}")
                print(f"FAIL {view}: missing {missing}")
            else:
                print(f"OK   {view}")

    if failures:
        raise SystemExit(1)
    print("\nall views rendered")


if __name__ == "__main__":
    main()
