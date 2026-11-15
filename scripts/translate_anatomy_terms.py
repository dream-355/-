"""Translate browser-visible anatomy names with a cached, strict JSON workflow."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.llm import _call_deepseek  # noqa: E402


MODEL_DIR = ROOT / "frontend" / "models"
BASE_TERMS = MODEL_DIR / "anatomy-terms-zh.json"
AUTO_TERMS = MODEL_DIR / "anatomy-terms-zh-auto.json"
FEMALE_MANIFEST = MODEL_DIR / "atlas-female.json"
BATCH_SIZE = 100

SYSTEM_PROMPT = """你是严谨的医学解剖术语翻译器。把输入的英文标准解剖名称翻译为规范、简洁的简体中文医学名称。
规则：
1. 保留左右、上下、前后、编号和分叶分段关系。
2. 使用中文解剖学通用术语，不添加原文没有的结构或解释。
3. 人名、综合征和无法确定标准译名的专名，保留英文原名。
4. 只返回一个合法 JSON 对象，键必须与输入字符串完全一致，值为中文字符串。
5. 不要返回 Markdown、注释、数组或任何额外文字。"""


def extract_json(text: str) -> dict[str, str]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object in translation response.")
    result = json.loads(text[start : end + 1])
    if not isinstance(result, dict):
        raise ValueError("Translation response is not an object.")
    return {
        str(key): str(value).strip()
        for key, value in result.items()
        if isinstance(value, str) and value.strip()
    }


def translate_batch(terms: list[str]) -> dict[str, str]:
    prompt = json.dumps(terms, ensure_ascii=False)
    response = _call_deepseek(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=5000,
    )
    translated = extract_json(response)
    missing = [term for term in terms if term not in translated]
    if missing:
        raise ValueError(f"Translation response missed {len(missing)} terms.")
    return translated


def main() -> None:
    female = json.loads(FEMALE_MANIFEST.read_text(encoding="utf-8"))
    known = json.loads(BASE_TERMS.read_text(encoding="utf-8")).get("terms", {})
    cache = {}
    if AUTO_TERMS.exists():
        cache = json.loads(AUTO_TERMS.read_text(encoding="utf-8")).get("terms", {})

    names = sorted(
        {
            part["name"].strip()
            for part in female["parts"]
            if part["name"].strip().lower() not in known
            and not re.search(r"[\u3400-\u9fff]", part["name"])
        }
    )
    pending = [name for name in names if name.lower() not in cache]
    print(f"Visible English names: {len(names)}; pending: {len(pending)}")

    for offset in range(0, len(pending), BATCH_SIZE):
        batch = pending[offset : offset + BATCH_SIZE]
        print(f"Translating {offset + 1}-{offset + len(batch)} of {len(pending)}")
        try:
            translated = translate_batch(batch)
        except Exception as exc:
            print(f"Batch failed: {exc}", file=sys.stderr)
            raise
        cache.update({key.lower().strip(): value for key, value in translated.items()})
        AUTO_TERMS.write_text(
            json.dumps(
                {
                    "version": "HRA female zh terminology",
                    "language": "zh-CN",
                    "terms": dict(sorted(cache.items())),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    missing = [name for name in names if name.lower() not in cache]
    if missing:
        print(f"Still missing {len(missing)} translations", file=sys.stderr)
        raise SystemExit(1)
    print(f"Translated {len(names)} names into {AUTO_TERMS}")


if __name__ == "__main__":
    main()
