"""Expose the non-sex-specific cranial bones already embedded in the female atlas."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEMALE_MANIFEST = ROOT / "frontend" / "models" / "atlas-female.json"
SKULL_IDS = {f"BM{index:04d}" for index in range(22)}


def main() -> None:
    atlas = json.loads(FEMALE_MANIFEST.read_text(encoding="utf-8"))
    changed = 0
    for part in atlas["parts"]:
        if part["id"] in SKULL_IDS:
            part["system"] = "skull"
            changed += 1
    if changed != len(SKULL_IDS):
        raise RuntimeError(f"Expected 22 female cranial parts, found {changed}")
    atlas["skullSupplement"] = {
        "source": "BodyParts3D 4.0",
        "scope": "Non-sex-specific cranial and facial support bones",
        "structures": changed,
        "method": "Already registered to the female body; exposed as a separate display system.",
    }
    FEMALE_MANIFEST.write_text(
        json.dumps(atlas, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"female skull structures exposed: {changed}")


if __name__ == "__main__":
    main()
