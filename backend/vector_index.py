from __future__ import annotations

import json
import os
import pickle
import re
import threading
from pathlib import Path
from typing import Any

import numpy as np

from backend.config import ROOT_DIR


CATALOG_PATH = ROOT_DIR / "backend" / "data" / "entity_catalog.jsonl"
CACHE_PATH = ROOT_DIR / "backend" / "data" / "vector_cache.pkl"

# Hashed feature space. Stay at 4096: the index is stored sparsely, so the
# dimension count costs disk only through the inverted-list keys.
HASH_DIMENSIONS = int(os.getenv("MEDICAL_VECTOR_DIM", "4096"))
CACHE_VERSION = 4

# Lay terminology mapped onto formal entity names. This is a curated synonym
# layer, not a trained embedding model.
SYNONYMS: dict[str, list[str]] = {
    "高血压": ["血压高", "高血压病", "原发性高血压"],
    "糖尿病": ["血糖高", "消渴"],
    "发热": ["发烧", "体温升高"],
    "头晕": ["眩晕", "头昏"],
    "腹泻": ["拉肚子", "水样便"],
    "心悸": ["心慌", "心跳快"],
    "胃痛": ["胃疼", "上腹痛"],
    "乏力": ["疲劳", "没力气", "全身无力"],
    "失眠": ["睡不着", "入睡困难"],
    "鼻塞": ["鼻子不通", "鼻堵"],
    "皮疹": ["疹子", "皮肤起疹"],
    "贫血": ["血红蛋白低", "血色素低"],
    "咳嗽": ["干咳", "咳痰"],
    "便秘": ["排便困难"],
    "耳鸣": ["耳朵响"],
    "感冒": ["伤风", "上呼吸道感染"],
    "咽痛": ["嗓子疼", "喉咙痛"],
    "胸闷": ["胸口闷", "胸部压迫感"],
    "水肿": ["浮肿", "肿胀"],
}


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", (text or "").lower())


def _tokenize(text: str) -> list[str]:
    """Character bigrams/trigrams/quadgrams for Chinese entity names."""
    cleaned = _normalize(text)
    if not cleaned:
        return []
    if len(cleaned) <= 2:
        return [cleaned]
    tokens: list[str] = []
    for size in (2, 3, 4):
        if len(cleaned) < size:
            continue
        for index in range(len(cleaned) - size + 1):
            tokens.append(cleaned[index : index + size])
    return tokens


def _synonym_text(text: str) -> str:
    extras: list[str] = []
    for term, aliases in SYNONYMS.items():
        if term in text:
            extras.extend(aliases)
        if any(alias in text for alias in aliases):
            extras.append(term)
    return " ".join(extras)


def _hash_token(token: str, dimensions: int) -> int:
    value = 2166136261
    for character in token:
        value ^= ord(character)
        value = (value * 16777619) & 0xFFFFFFFF
    return value % dimensions


def _sparse_vector(
    tokens: list[str],
    idf: dict[str, float] | None,
    dimensions: int,
) -> dict[int, float]:
    """Sublinear TF x IDF projected into hashed dimensions, L2 normalised."""
    if not tokens:
        return {}
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    vector: dict[int, float] = {}
    for token, count in counts.items():
        weight = 1.0 + float(np.log(count))
        if idf is not None:
            weight *= idf.get(token, 0.0)
        if weight == 0.0:
            continue
        key = _hash_token(token, dimensions)
        vector[key] = vector.get(key, 0.0) + weight
    norm = float(np.sqrt(sum(value * value for value in vector.values()))) or 1.0
    return {key: value / norm for key, value in vector.items()}


class EntityVectorIndex:
    """Sparse TF-IDF vector recall for Chinese medical entities.

    Documents are stored as an inverted index (dimension -> row ids and
    weights) instead of a dense matrix. This keeps the 80k-entity index at
    tens of megabytes rather than gigabytes, which matters on a small cloud
    instance, and makes query scoring a handful of vectorised gathers.
    """

    def __init__(self, catalog_path: Path = CATALOG_PATH) -> None:
        self.catalog_path = catalog_path
        self._lock = threading.Lock()
        self._ready = False
        self._entities: list[dict[str, str]] = []
        self._inverted: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        self._idf: dict[str, float] | None = None
        self._dimensions = HASH_DIMENSIONS
        self._terms = 0
        self._error: str | None = None

    def _load_cache(self) -> bool:
        if not CACHE_PATH.exists():
            return False
        try:
            with CACHE_PATH.open("rb") as cache:
                payload = pickle.load(cache)
            if payload.get("version") != CACHE_VERSION:
                return False
            self._entities = payload["entities"]
            self._inverted = payload["inverted"]
            self._idf = payload.get("idf")
            self._dimensions = payload.get("dimensions", HASH_DIMENSIONS)
            self._terms = payload.get("terms", 0)
            return bool(self._entities) and bool(self._inverted)
        except Exception:
            return False

    def _build(self) -> None:
        entities: list[dict[str, str]] = []
        tokenized: list[list[str]] = []
        with self.catalog_path.open("r", encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                item = json.loads(line)
                name = item.get("name", "")
                if not name:
                    continue
                entities.append(item)
                tokenized.append(
                    _tokenize(name + " " + _synonym_text(name))
                )
        if not entities:
            return

        document_frequency: dict[str, int] = {}
        for tokens in tokenized:
            for token in set(tokens):
                document_frequency[token] = document_frequency.get(token, 0) + 1
        total = len(tokenized)
        idf = {
            token: float(np.log((1.0 + total) / (1.0 + frequency)) + 1.0)
            for token, frequency in document_frequency.items()
        }

        rows_by_dim: dict[int, list[int]] = {}
        weights_by_dim: dict[int, list[float]] = {}
        for row, tokens in enumerate(tokenized):
            vector = _sparse_vector(tokens, idf, HASH_DIMENSIONS)
            for dimension, weight in vector.items():
                rows_by_dim.setdefault(dimension, []).append(row)
                weights_by_dim.setdefault(dimension, []).append(weight)

        inverted = {
            dimension: (
                np.asarray(rows_by_dim[dimension], dtype=np.int32),
                np.asarray(weights_by_dim[dimension], dtype=np.float32),
            )
            for dimension in rows_by_dim
        }

        self._entities = entities
        self._inverted = inverted
        self._idf = idf
        self._dimensions = HASH_DIMENSIONS
        self._terms = len(document_frequency)

        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with CACHE_PATH.open("wb") as cache:
                pickle.dump(
                    {
                        "version": CACHE_VERSION,
                        "entities": entities,
                        "inverted": inverted,
                        "idf": idf,
                        "dimensions": self._dimensions,
                        "terms": self._terms,
                    },
                    cache,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
        except OSError:
            pass

    def _load(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            if not self._load_cache():
                try:
                    self._build()
                except FileNotFoundError:
                    self._error = "vector catalog is missing"
                except Exception as exc:
                    self._error = type(exc).__name__
            self._ready = True

    def warmup(self) -> None:
        self._load()

    def memory_bytes(self) -> int:
        self._load()
        total = 0
        for rows, weights in self._inverted.values():
            total += rows.nbytes + weights.nbytes
        return total + len(self._entities) * 120

    def stats(self) -> dict[str, Any]:
        self._load()
        return {
            "ready": self._ready and not self._error,
            "entities": len(self._entities),
            "dimensions": self._dimensions,
            "terms": self._terms,
            "synonyms": len(SYNONYMS),
            "storage": "sparse inverted index",
            "weighting": "sublinear-tf x smoothed-idf, l2-normalised",
            "approx_memory_mb": round(self.memory_bytes() / 1_048_576, 1),
            "error": self._error,
        }

    def search(self, query: str, limit: int = 12) -> list[dict[str, Any]]:
        self._load()
        if not self._entities or not self._inverted:
            return []
        tokens = _tokenize(query + " " + _synonym_text(query))
        if not tokens:
            return []
        query_vector = _sparse_vector(tokens, self._idf, self._dimensions)
        if not query_vector:
            return []

        scores = np.zeros(len(self._entities), dtype=np.float32)
        for dimension, weight in query_vector.items():
            entry = self._inverted.get(dimension)
            if entry is None:
                continue
            rows, weights = entry
            scores[rows] += weights * weight

        normalized_query = _normalize(query)
        if normalized_query:
            # Exact containment bonus so identical entity names rank first.
            for index, entity in enumerate(self._entities):
                name = _normalize(entity.get("name", ""))
                if name and (name == normalized_query or name in normalized_query):
                    scores[index] += 0.25

        order = np.argsort(-scores)
        results: list[dict[str, Any]] = []
        for index in order:
            score = float(scores[index])
            if score < 0.08:
                break
            entity = dict(self._entities[int(index)])
            entity["score"] = round(score, 4)
            entity["match_type"] = "vector"
            results.append(entity)
            if len(results) >= limit:
                break
        return results


vector_index = EntityVectorIndex()
