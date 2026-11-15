from __future__ import annotations

import re
import threading
import time
from collections import defaultdict
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from backend.config import settings
from backend.vector_index import vector_index


RELATION_LABELS = {
    "symptomAndSign": "症状与体征",
    "relatedSymptom": "相关症状",
    "complication": "并发症",
    "cause": "可能病因",
    "pathogenesis": "发病机制",
    "pathophysiology": "病理生理",
    "check": "相关检查",
    "auxiliaryExamination": "辅助检查",
    "checkSubject": "检查项目",
    "diagnosis": "诊断相关",
    "treatmentPrograms": "治疗方案",
    "treatment": "治疗",
    "drugTherapy": "药物治疗",
    "operation": "手术相关",
    "department": "就诊科室",
    "precautions": "注意事项",
    "adverseReactions": "不良反应",
    "contraindications": "禁忌",
    "prognosis": "预后",
    "prognosticSurvivalTime": "生存期",
    "diseaseSite": "发病部位",
    "pathologicalType": "病理类型",
    "stage": "分期",
    "relatedDisease": "相关疾病",
    "spreadWay": "传播途径",
    "infectious": "传染性",
}


LABEL_LABELS = {
    "Disease": "疾病",
    "Drug": "药品",
    "Symptom": "症状",
    "SymptomAndSign": "症状体征",
    "Check": "检查",
    "Department": "科室",
    "Treatment": "治疗",
    "Operation": "手术",
    "Complication": "并发症",
    "Cause": "病因",
    "Precautions": "注意事项",
}


CLARIFY_HINTS: dict[str, list[str]] = {
    "treatment": ["症状持续了多久", "已经用过哪些药、效果如何", "是否有药物过敏史或基础疾病"],
    "examination": ["症状出现的时间与变化过程", "是否有发热、疼痛等伴随表现", "既往是否做过相关检查"],
    "department": ["主要不适的具体部位", "年龄以及是否有外伤史", "症状是否持续加重"],
    "cause": ["症状出现的诱因", "持续时间与加重缓解因素", "既往病史与正在使用的药物"],
    "symptom": ["症状开始的时间", "是否有其他伴随症状", "是否正在服药"],
    "complication": ["确诊时间与目前控制情况", "最近一次检查结果", "是否出现新的不适"],
    "prevention": ["目前正在使用的药物", "是否有过敏史或基础疾病", "生活方式与既往发作情况"],
}
DEFAULT_CLARIFY = ["具体症状与持续时间", "年龄与既往病史", "正在使用的药物或过敏史"]


INTENT_KEYWORDS = {
    "assessment": r"怎么判断|如何判断|判断自己|如何区分|怎么区分|是不是|是否患|自查|怎么办|怎么处理",
    "complication": r"并发症|会发展成|会引起什么病|可能引起",
    "treatment": r"药|治疗|缓解|怎么治|服用|用药|吃什么",
    "examination": r"检查|化验|报告|指标|检测|体检|数值",
    "department": r"什么科|挂哪科|科室|看什么医生",
    "cause": r"原因|为什么|怎么会|病因|引起",
    "symptom": r"症状|表现|感觉|头晕|疼痛|不舒服",
    "prevention": r"注意|禁忌|预防|避免|不能",
}

INTENT_RELATIONS = {
    "assessment": [
        "symptomAndSign",
        "relatedSymptom",
        "complication",
        "cause",
        "check",
        "auxiliaryExamination",
        "department",
        "precautions",
    ],
    "complication": ["complication", "relatedDisease", "relatedSymptom"],
    "treatment": [
        "drugTherapy",
        "treatmentPrograms",
        "treatment",
        "indications",
        "contraindications",
        "adverseReactions",
        "precautions",
        "relatedDisease",
    ],
    "examination": [
        "check",
        "auxiliaryExamination",
        "checkSubject",
        "diagnosis",
        "relatedDisease",
        "department",
    ],
    "department": ["department"],
    "cause": [
        "cause",
        "pathogenesis",
        "pathophysiology",
        "relatedDisease",
        "relatedSymptom",
        "symptomAndSign",
        "complication",
    ],
    "symptom": [
        "symptomAndSign",
        "relatedSymptom",
        "complication",
        "cause",
        "department",
    ],
    "prevention": [
        "precautions",
        "contraindications",
        "adverseReactions",
        "spreadWay",
    ],
}

TYPE_PRIORITY = {
    "Disease": 0,
    "Drug": 1,
    "Symptom": 2,
    "SymptomAndSign": 3,
    "Check": 4,
    "Department": 5,
    "Treatment": 6,
    "Precautions": 7,
}

DISEASE_COMPLICATION_TERMS = {
    "高血压": [
        "心脏",
        "脑",
        "卒中",
        "中风",
        "肾",
        "视网膜",
        "动脉",
        "心力衰竭",
        "梗死",
        "危象",
    ],
    "糖尿病": ["视网膜", "肾病", "神经", "足", "心血管", "酮症", "感染"],
    "冠心病": ["心力衰竭", "心律失常", "心肌梗死", "休克"],
    "痛风": ["痛风石", "肾病", "关节", "尿酸性"],
}


def detect_intent(text: str) -> str:
    for intent in (
        "assessment",
        "complication",
        "prevention",
        "treatment",
        "examination",
        "department",
        "cause",
        "symptom",
    ):
        if re.search(INTENT_KEYWORDS[intent], text or ""):
            return intent
    return "general"


def longest_common_substring_length(left: str, right: str) -> int:
    left = re.sub(r"\W+", "", left or "").lower()
    right = re.sub(r"\W+", "", right or "").lower()
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    best = 0
    for left_char in left:
        current = [0] * (len(right) + 1)
        for index, right_char in enumerate(right, start=1):
            if left_char == right_char:
                current[index] = previous[index - 1] + 1
                best = max(best, current[index])
        previous = current
    return best


def query_focus_terms(question: str, entities: list[dict[str, Any]]) -> list[str]:
    focus = []
    for phrase, synonyms in QUERY_SYNONYMS.items():
        if phrase in question:
            focus.extend(synonyms)
    for entity in entities:
        name = entity.get("name", "")
        if name and name in question:
            focus.append(name)
    return list(dict.fromkeys(focus))


def semantic_relation_label(
    relation: str,
    subject_type: str = "",
    object_type: str = "",
) -> str:
    if subject_type == "Symptom" and object_type == "Disease":
        if relation in {"relatedSymptom", "symptomAndSign", "complication"}:
            return "相关疾病"
    return RELATION_LABELS.get(relation, relation)


def population_is_relevant(
    fact: dict[str, Any],
    *,
    age: int | None,
    gender: str = "",
    pregnancy: bool = False,
) -> bool:
    object_name = fact.get("object", "")
    pediatric_terms = ("新生儿", "婴儿", "幼儿", "小儿", "儿童", "青少年")
    older_terms = ("老年", "老人", "高龄")
    pregnancy_terms = ("妊娠", "孕期", "产妇", "胎儿")
    if age is not None and age >= 18 and any(term in object_name for term in pediatric_terms):
        return False
    if age is not None and age < 65 and any(term in object_name for term in older_terms):
        return False
    if not pregnancy and any(term in object_name for term in pregnancy_terms):
        return False
    if gender != "男" and any(
        term in object_name
        for term in ("前列腺", "睾丸", "阴茎", "附睾")
    ):
        return False
    if gender == "男" and any(
        term in object_name
        for term in ("子宫", "卵巢", "宫颈", "妊娠", "月经", "产妇")
    ):
        return False
    return True


KEY_TERMS = [
    "感冒",
    "普通感冒",
    "流行性感冒",
    "头晕",
    "眩晕",
    "头痛",
    "发热",
    "咳嗽",
    "咽痛",
    "咽痒",
    "鼻塞",
    "流涕",
    "打喷嚏",
    "胸闷",
    "胸痛",
    "心悸",
    "呼吸困难",
    "腹痛",
    "腹泻",
    "恶心",
    "呕吐",
    "乏力",
    "失眠",
    "皮疹",
    "瘙痒",
    "水肿",
    "贫血",
    "高血压",
    "低血压",
    "糖尿病",
    "高血糖",
    "低血糖",
    "冠心病",
    "心肌梗死",
    "脑卒中",
    "偏头痛",
    "胃炎",
    "胃溃疡",
    "哮喘",
    "肺炎",
    "支气管炎",
    "过敏性鼻炎",
    "痛风",
    "甲状腺功能亢进",
    "甲状腺结节",
    "抑郁症",
    "焦虑",
    "痛经",
    "月经不调",
    "湿疹",
    "荨麻疹",
    "扭伤",
    "拉伤",
    "骨折",
    "外伤",
    "关节痛",
    "腰痛",
    "背痛",
    "颈椎病",
    "腰椎间盘突出",
]

ENTITY_QUERY_STOPWORDS = {
    "判断",
    "感觉",
    "认为",
    "可能",
    "如何",
    "是否",
    "怎么",
    "怎么办",
    "处理",
    "问题",
    "自我否定",
    "自我否定等",
    "往往",
}

QUERY_SYNONYMS = {
    "感冒": ["普通感冒"],
    "着凉": ["普通感冒"],
    "受凉": ["普通感冒"],
    "血红蛋白偏低": ["贫血"],
    "血红蛋白低": ["贫血"],
    "发烧": ["发热"],
    "心慌": ["心悸"],
    "拉肚子": ["腹泻"],
    "流鼻涕": ["流涕"],
    "血压高": ["高血压"],
    "血糖高": ["高血糖"],
    "嗓子疼": ["咽痛"],
    "嗓子痒": ["咽痒"],
}


class MedicalGraph:
    def __init__(self) -> None:
        self._driver = None
        self._stats_cache: dict[str, Any] | None = None
        self._stats_at = 0.0
        self._lock = threading.Lock()
        self._index_ready = False

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                connection_timeout=5,
            )
        return self._driver

    @staticmethod
    def detect_intent(text: str) -> str:
        return detect_intent(text)

    def health(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                version = session.run(
                    "CALL dbms.components() YIELD versions "
                    "RETURN versions[0] AS version"
                ).single()
            return {
                "online": True,
                "version": version["version"] if version else "Neo4j",
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            }
        except Exception as exc:
            return {
                "online": False,
                "version": None,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "error": type(exc).__name__,
            }

    def ensure_index(self) -> None:
        if self._index_ready:
            return
        with self._lock:
            if self._index_ready:
                return
            try:
                with self.driver.session(database=settings.neo4j_database) as session:
                    session.run(
                        """
                        CREATE FULLTEXT INDEX medical_entity_search IF NOT EXISTS
                        FOR (n:Disease|Drug|Symptom|SymptomAndSign|Check|Department|
                               Treatment|Operation|Diagnosis|Complication|Cause|Precautions)
                        ON EACH [n.name]
                        """
                    ).consume()
                self._index_ready = True
            except (Neo4jError, ServiceUnavailable):
                # Read-only fallback is handled for each query.
                self._index_ready = True

    def stats(self, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._stats_cache and now - self._stats_at < 60:
            return self._stats_cache
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                row = session.run(
                    """
                    MATCH (n)
                    WITH count(n) AS nodes
                    MATCH ()-[r]->()
                    RETURN nodes, count(r) AS relationships
                    """
                ).single()
                labels = session.run(
                    """
                    MATCH (n)
                    UNWIND labels(n) AS label
                    RETURN label, count(*) AS count
                    ORDER BY count DESC
                    """
                ).data()
            self._stats_cache = {
                "online": True,
                "nodes": row["nodes"] if row else 0,
                "relationships": row["relationships"] if row else 0,
                "label_count": len(labels),
                "labels": labels,
            }
            self._stats_at = now
            return self._stats_cache
        except Exception as exc:
            return {
                "online": False,
                "nodes": 0,
                "relationships": 0,
                "label_count": 0,
                "labels": [],
                "error": type(exc).__name__,
            }

    def search_entities(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        term = (query or "").strip()
        if not term:
            return []
        self.ensure_index()
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                rows = session.run(
                    """
                    CALL db.index.fulltext.queryNodes(
                        'medical_entity_search', $term, {limit: $limit}
                    )
                    YIELD node, score
                    RETURN elementId(node) AS id,
                           labels(node)[0] AS type,
                           node.name AS name,
                           score
                    ORDER BY score DESC
                    """,
                    term=term,
                    limit=limit,
                ).data()
            return [
                {
                    **row,
                    "type_label": LABEL_LABELS.get(row["type"], row["type"]),
                    "score": round(float(row["score"]), 3),
                }
                for row in rows
                if row["name"]
            ]
        except Exception:
            return self._fallback_search(term, limit)

    def _fallback_search(self, term: str, limit: int) -> list[dict[str, Any]]:
        allowed = [
            "Disease",
            "Drug",
            "Symptom",
            "SymptomAndSign",
            "Check",
            "Department",
        ]
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                rows = session.run(
                    """
                    MATCH (n)
                    WHERE any(label IN labels(n) WHERE label IN $labels)
                      AND n.name CONTAINS $term
                    RETURN elementId(n) AS id, labels(n)[0] AS type,
                           n.name AS name, 1.0 AS score
                    LIMIT $limit
                    """,
                    labels=allowed,
                    term=term,
                    limit=limit,
                ).data()
            return [
                {
                    **row,
                    "type_label": LABEL_LABELS.get(row["type"], row["type"]),
                }
                for row in rows
            ]
        except Exception:
            return []

    def hybrid_search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Blend Neo4j full-text lookup with local Chinese n-gram vectors."""
        lexical = self.search_entities(query, max(limit * 2, 8))
        semantic = vector_index.search(query, max(limit * 2, 8))
        if not lexical:
            lexical = self._fallback_search(query, max(limit * 2, 8))
        max_lexical = max((float(item.get("score", 0)) for item in lexical), default=1)
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for rank, item in enumerate(lexical):
            key = (item.get("name", ""), item.get("type", ""))
            score = 0.58 * (float(item.get("score", 0)) / max_lexical) + max(0, 0.08 - rank * 0.01)
            merged[key] = {**item, "_hybrid_score": score, "match_type": "lexical"}
        for rank, item in enumerate(semantic):
            key = (item.get("name", ""), item.get("type", ""))
            score = 0.42 * float(item.get("score", 0)) + max(0, 0.06 - rank * 0.007)
            if key in merged:
                merged[key]["_hybrid_score"] += score
                merged[key]["match_type"] = "hybrid"
            else:
                merged[key] = {**item, "_hybrid_score": score}
        for item in merged.values():
            affinity = longest_common_substring_length(query, item.get("name", ""))
            if affinity >= 2:
                item["_hybrid_score"] += 0.045 * affinity * affinity
            normalized_query = re.sub(r"\W+", "", query)
            normalized_name = re.sub(r"\W+", "", item.get("name", ""))
            if normalized_name and (
                normalized_name in normalized_query
                or normalized_query in normalized_name
            ):
                item["_hybrid_score"] += 0.35
        deduplicated: dict[str, dict[str, Any]] = {}
        for item in sorted(
            merged.values(),
            key=lambda value: (
                value["_hybrid_score"],
                -TYPE_PRIORITY.get(value.get("type"), 20),
            ),
            reverse=True,
        ):
            name = item.get("name", "")
            if not name:
                continue
            current = deduplicated.get(name)
            if current is None and len(deduplicated) < limit:
                item["score"] = round(float(item["_hybrid_score"]), 4)
                deduplicated[name] = item
        return list(deduplicated.values())

    def extract_entities(self, question: str) -> list[dict[str, Any]]:
        terms = [term for term in KEY_TERMS if term in question]
        for phrase, synonyms in QUERY_SYNONYMS.items():
            if phrase in question:
                terms.extend(synonyms)
        terms.sort(key=len, reverse=True)
        # Keep a small number of strong mentions and avoid overlapping near-duplicates.
        selected: list[str] = []
        for term in terms:
            if not any(term in existing for existing in selected):
                selected.append(term)

        entities: list[dict[str, Any]] = []
        seen_names: set[tuple[str, str]] = set()
        preferred_types = {
            "Disease": 0,
            "Diagnosis": 1,
            "SymptomAndSign": 2,
            "Symptom": 3,
            "Complication": 4,
            "Cause": 5,
            "Check": 6,
            "Department": 7,
            "Treatment": 8,
            "Drug": 9,
        }
        if selected:
            for term in selected[:4]:
                candidates: list[dict[str, Any]] = []
                for item in self.hybrid_search(term, 8):
                    name = item.get("name", "")
                    if (
                        not name
                        or name in ENTITY_QUERY_STOPWORDS
                        or not (
                            name == term
                            or term in name
                            or (len(name) >= 2 and name in question)
                        )
                    ):
                        continue
                    exact = name == term or term in name
                    candidates.append(
                        {
                            **item,
                            "_entity_rank": (
                                0 if exact else 1,
                                preferred_types.get(item.get("type"), 20),
                                len(name),
                            ),
                        }
                    )
                candidates.sort(key=lambda item: item["_entity_rank"])
                if not candidates:
                    item = {
                        "id": f"local-term:{term}",
                        "name": term,
                        "type": "MedicalConcept",
                        "score": 0.0,
                    }
                else:
                    item = candidates[0]
                key = (item["name"], item["type"])
                if key in seen_names:
                    continue
                seen_names.add(key)
                entities.append(item)
                if len(entities) >= 4:
                    break
        else:
            semantic = [
                item
                for item in self.hybrid_search(question, 6)
                if float(item.get("score", 0)) >= 0.55
                and item.get("name") not in ENTITY_QUERY_STOPWORDS
                and (
                    longest_common_substring_length(
                        question, item.get("name", "")
                    )
                    >= 2
                    or float(item.get("score", 0)) >= 0.78
                )
            ]
            for item in semantic:
                key = (item["name"], item["type"])
                if key in seen_names:
                    continue
                seen_names.add(key)
                entities.append(item)
        return entities

    def neighborhood(
        self,
        node_id: str,
        name: str = "",
        limit: int = 42,
        depth: int = 1,
    ) -> dict[str, Any]:
        """Return a focused graph with explicit root, direct and outer levels."""
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                rows = session.run(
                    """
                    MATCH (n)
                    WHERE elementId(n) = $node_id
                    OPTIONAL MATCH (n)-[r]-(m)
                    RETURN n.name AS center_name,
                           labels(n)[0] AS center_type,
                           collect({
                               relation: type(r),
                               name: m.name,
                               type: labels(m)[0],
                               id: elementId(m)
                           })[0..$limit] AS neighbors
                    """,
                    node_id=node_id,
                    limit=limit,
                ).single()
                if not rows:
                    return {"center": None, "nodes": [], "edges": [], "facts": []}

                center = {
                    "id": node_id,
                    "name": rows["center_name"] or name,
                    "type": rows["center_type"],
                    "level": 0,
                }
                neighbors = [
                    item
                    for item in rows["neighbors"]
                    if item and item.get("name") and item.get("relation")
                ]
                priority = {
                    "symptomAndSign": 0,
                    "relatedSymptom": 1,
                    "department": 2,
                    "check": 3,
                    "auxiliaryExamination": 4,
                    "cause": 5,
                    "complication": 6,
                    "drugTherapy": 7,
                    "treatmentPrograms": 8,
                    "precautions": 9,
                }
                neighbors.sort(key=lambda item: priority.get(item["relation"], 20))

                nodes_by_id: dict[str, dict[str, Any]] = {node_id: center}
                edges_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
                facts: list[dict[str, Any]] = []
                for item in neighbors:
                    target_id = item["id"]
                    if target_id and target_id not in nodes_by_id:
                        nodes_by_id[target_id] = {
                            "id": target_id,
                            "name": item["name"],
                            "type": item["type"],
                            "level": 1,
                        }
                    edge = {
                        "source": node_id,
                        "target": target_id,
                        "type": item["relation"],
                        "label": RELATION_LABELS.get(
                            item["relation"], item["relation"]
                        ),
                        "level": 1,
                    }
                    edges_by_key[(edge["source"], edge["target"], edge["type"])] = edge
                    facts.append(
                        {
                            "relation": item["relation"],
                            "subject": center["name"],
                            "predicate": semantic_relation_label(
                                item["relation"], center["type"], item["type"]
                            ),
                            "object": item["name"],
                            "subject_type": center["type"],
                            "object_type": item["type"],
                            "subject_id": node_id,
                            "object_id": target_id,
                            "level": 1,
                        }
                    )

                if depth >= 2:
                    direct_ids = [
                        node["id"]
                        for node in nodes_by_id.values()
                        if node.get("level") == 1
                    ][:14]
                    if direct_ids:
                        outer_rows = session.run(
                            """
                            UNWIND $source_ids AS source_id
                            MATCH (source)
                            WHERE elementId(source) = source_id
                            MATCH (source)-[r]-(target)
                            WHERE NOT elementId(target) IN $excluded_ids
                            RETURN elementId(source) AS source_id,
                                   source.name AS source_name,
                                   labels(source)[0] AS source_type,
                                   type(r) AS relation,
                                   elementId(target) AS target_id,
                                   target.name AS target_name,
                                   labels(target)[0] AS target_type
                            LIMIT $outer_limit
                            """,
                            source_ids=direct_ids,
                            excluded_ids=list(nodes_by_id.keys()),
                            outer_limit=54,
                        ).data()
                        for row in outer_rows:
                            target_id = row["target_id"]
                            if not target_id or not row["target_name"]:
                                continue
                            if target_id not in nodes_by_id:
                                nodes_by_id[target_id] = {
                                    "id": target_id,
                                    "name": row["target_name"],
                                    "type": row["target_type"],
                                    "level": 2,
                                }
                            edge = {
                                "source": row["source_id"],
                                "target": target_id,
                                "type": row["relation"],
                                "label": RELATION_LABELS.get(
                                    row["relation"], row["relation"]
                                ),
                                "level": 2,
                            }
                            edges_by_key[
                                (edge["source"], edge["target"], edge["type"])
                            ] = edge
                            facts.append(
                                {
                                    "relation": row["relation"],
                                    "subject": row["source_name"],
                                    "predicate": semantic_relation_label(
                                        row["relation"],
                                        row["source_type"],
                                        row["target_type"],
                                    ),
                                    "object": row["target_name"],
                                    "subject_type": row["source_type"],
                                    "object_type": row["target_type"],
                                    "subject_id": row["source_id"],
                                    "object_id": target_id,
                                    "level": 2,
                                }
                            )

                return {
                    "center": center,
                    "nodes": list(nodes_by_id.values()),
                    "edges": list(edges_by_key.values()),
                    "facts": facts,
                }
        except Exception:
            return {"center": None, "nodes": [], "edges": [], "facts": []}

    def build_context(
        self,
        question: str,
        *,
        age: int | None = None,
        gender: str = "",
        pregnancy: bool = False,
        intent_override: str | None = None,
    ) -> dict[str, Any]:
        entities = self.extract_entities(question)
        intent = intent_override or detect_intent(question)
        nodes: dict[str, dict[str, Any]] = {}
        edge_map: dict[tuple[str, str, str], dict[str, Any]] = {}
        raw_facts: list[dict[str, Any]] = []

        for entity in entities:
            if str(entity.get("id", "")).startswith("local-term:"):
                continue
            detail = self.neighborhood(entity["id"], entity["name"], 32, depth=1)
            for node in detail["nodes"]:
                nodes[node["id"]] = node
            for edge in detail["edges"]:
                edge_map[(edge["source"], edge["target"], edge["type"])] = edge
            for fact in detail["facts"]:
                if not population_is_relevant(
                    fact,
                    age=age,
                    gender=gender,
                    pregnancy=pregnancy,
                ):
                    continue
                identity = (
                    fact.get("subject_id"),
                    fact.get("relation"),
                    fact.get("object_id"),
                )
                if identity not in {
                    (
                        existing.get("subject_id"),
                        existing.get("relation"),
                        existing.get("object_id"),
                    )
                    for existing in raw_facts
                }:
                    raw_facts.append(fact)

        allowed = INTENT_RELATIONS.get(intent, [])
        if allowed:
            filtered = [fact for fact in raw_facts if fact.get("relation") in allowed]
        else:
            filtered = raw_facts
        entity_names = {
            entity.get("name", "")
            for entity in entities
            if entity.get("name")
        }
        if entity_names:
            filtered = [
                fact
                for fact in filtered
                if fact.get("subject") in entity_names
                or fact.get("object") in entity_names
            ]
        if intent == "complication":
            disease_names = {
                entity.get("name", "")
                for entity in entities
                if entity.get("type") == "Disease"
            }
            for disease_name, complication_terms in DISEASE_COMPLICATION_TERMS.items():
                if disease_name not in disease_names and disease_name not in question:
                    continue
                curated = [
                    fact
                    for fact in filtered
                    if fact.get("relation") == "complication"
                    and any(term in fact.get("object", "") for term in complication_terms)
                ]
                if curated:
                    filtered = curated
                    break
        focus_terms = query_focus_terms(question, entities)
        if intent == "examination" and focus_terms:
            exact_context = [
                fact
                for fact in filtered
                if any(
                    term in fact.get("object", "")
                    for term in focus_terms
                )
                or fact.get("relation")
                in {"check", "auxiliaryExamination", "checkSubject"}
            ]
            if exact_context:
                filtered = exact_context

        indirect_used = False
        if not filtered and entities:
            for entity in entities[:3]:
                try:
                    detail = self.neighborhood(
                        entity["id"], entity["name"], 24, depth=2
                    )
                except (Neo4jError, ServiceUnavailable):
                    continue
                for fact in detail.get("facts", []):
                    if allowed and fact.get("relation") not in allowed:
                        continue
                    if not population_is_relevant(
                        fact,
                        age=age,
                        gender=gender,
                        pregnancy=pregnancy,
                    ):
                        continue
                    fact["indirect"] = True
                    filtered.append(fact)
                    if len(filtered) >= 12:
                        break
                if filtered:
                    indirect_used = True
                    break
            raw_facts.extend(filtered)

        def focus_rank(fact: dict[str, Any]) -> int:
            if any(term in fact.get("object", "") for term in focus_terms):
                return 0
            if any(term in fact.get("subject", "") for term in focus_terms):
                return 1
            return 2

        relation_priority = {value: index for index, value in enumerate(allowed)}
        filtered.sort(
            key=lambda fact: (
                focus_rank(fact),
                fact.get("level", 2),
                relation_priority.get(fact.get("relation"), 50),
                -TYPE_PRIORITY.get(fact.get("subject_type"), 20),
                -TYPE_PRIORITY.get(fact.get("object_type"), 20),
            )
        )
        facts = filtered[:18]
        citations = []
        sections: dict[str, list[str]] = defaultdict(list)
        focused_fact_count = 0
        for index, fact in enumerate(facts, start=1):
            citation_id = f"E{index}"
            fact["citation_id"] = citation_id
            fact["source"] = "Neo4j 医疗知识图谱"
            fact["relevance"] = "focus" if focus_rank(fact) == 0 else "context"
            if fact["relevance"] == "focus":
                focused_fact_count += 1
            citations.append(
                {
                    "id": citation_id,
                    "subject": fact["subject"],
                    "subject_type": fact["subject_type"],
                    "predicate": fact["predicate"],
                    "object": fact["object"],
                    "object_type": fact["object_type"],
                    "subject_id": fact["subject_id"],
                    "object_id": fact["object_id"],
                    "source": fact["source"],
                    "evidence_level": "indirect" if fact.get("indirect") else "direct",
                }
            )
            if fact["object"] not in sections[fact["predicate"]]:
                sections[fact["predicate"]].append(fact["object"])

        clarification = (
            {
                "reason": "当前图谱证据不足，需要补充信息后再判断",
                "needed": CLARIFY_HINTS.get(intent, DEFAULT_CLARIFY),
            }
            if not facts
            else None
        )

        return {
            "question": question,
            "entities": entities,
            "nodes": list(nodes.values()),
            "edges": list(edge_map.values()),
            "facts": facts,
            "citations": citations,
            "sections": {
                key: values[:10] for key, values in list(sections.items())[:12]
            },
            "intent": intent,
            "clarification": clarification,
            "retrieval": {
                "strategy": "Neo4j full-text + local character-vector recall",
                "vector_index": vector_index.stats(),
                "raw_fact_count": len(raw_facts),
                "filtered_fact_count": len(facts),
                "evidence_level": (
                    "indirect" if indirect_used else "direct" if facts else "none"
                ),
                "excluded_relation_count": len(raw_facts) - len(filtered),
                "population_filtered": age is not None or bool(gender),
                "focused_fact_count": focused_fact_count,
                "evidence_quality": (
                    "high"
                    if focused_fact_count >= 2
                    or (
                        intent in {"complication", "examination"}
                        and len(facts) >= 2
                    )
                    else "medium"
                    if focused_fact_count == 1 or facts
                    else "insufficient"
                ),
            },
            "source": "Neo4j 医疗知识图谱",
        }

    def showcase_graph(self) -> dict[str, Any]:
        names = ["高血压", "糖尿病", "冠心病", "肺炎", "偏头痛", "哮喘"]
        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                rows = session.run(
                    """
                    MATCH (n:Disease)
                    WHERE n.name IN $names
                    OPTIONAL MATCH (n)-[r]->(m)
                    WITH n, r, m
                    ORDER BY CASE type(r)
                        WHEN 'symptomAndSign' THEN 1
                        WHEN 'relatedSymptom' THEN 2
                        WHEN 'department' THEN 3
                        WHEN 'check' THEN 4
                        ELSE 8 END
                    RETURN n.name AS source_name,
                           labels(n)[0] AS source_type,
                           elementId(n) AS source_id,
                           type(r) AS relation,
                           m.name AS target_name,
                           labels(m)[0] AS target_type,
                           elementId(m) AS target_id
                    LIMIT 90
                    """,
                    names=names,
                ).data()
            nodes: dict[str, dict[str, Any]] = {}
            edges: dict[tuple[str, str, str], dict[str, Any]] = {}
            for row in rows:
                nodes[row["source_id"]] = {
                    "id": row["source_id"],
                    "name": row["source_name"],
                    "type": row["source_type"],
                }
                if row["target_id"] and row["target_name"]:
                    nodes[row["target_id"]] = {
                        "id": row["target_id"],
                        "name": row["target_name"],
                        "type": row["target_type"],
                    }
                    edge = {
                        "source": row["source_id"],
                        "target": row["target_id"],
                        "type": row["relation"],
                        "label": RELATION_LABELS.get(row["relation"], row["relation"]),
                    }
                    edges[(edge["source"], edge["target"], edge["type"])] = edge
            return {
                "nodes": list(nodes.values())[:64],
                "edges": list(edges.values())[:90],
                "source": "Neo4j 医疗知识图谱",
            }
        except Exception:
            return {"nodes": [], "edges": [], "source": "Neo4j 医疗知识图谱"}

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None


medical_graph = MedicalGraph()

