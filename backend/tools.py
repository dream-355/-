from __future__ import annotations

import time
from typing import Any, Callable

from backend.graph import medical_graph
from backend.medications import recommend_medications
from backend.safety import health_overview, longitudinal_insights, triage


def search_medical_entities(query: str, limit: int = 8) -> dict[str, Any]:
    results = medical_graph.hybrid_search(query, min(max(limit, 1), 20))
    return {
        "query": query,
        "intent": medical_graph.detect_intent(query),
        "results": results,
    }


def expand_medical_entity(
    node_id: str = "",
    name: str = "",
    depth: int = 1,
) -> dict[str, Any]:
    if not node_id and name:
        matches = medical_graph.hybrid_search(name, 1)
        if matches:
            node_id = matches[0]["id"]
    if not node_id:
        return {"error": "entity not found"}
    return medical_graph.neighborhood(
        node_id,
        name=name,
        limit=32,
        depth=min(max(depth, 1), 2),
    )


def assess_symptoms(
    symptoms: str,
    duration_days: int | None = None,
    age: int | None = None,
    pregnancy: bool = False,
) -> dict[str, Any]:
    return triage(
        symptoms,
        duration_days=duration_days,
        age=age,
        pregnancy=pregnancy,
    )


def medication_options(
    symptoms: str,
    age: int | None = None,
    pregnancy: bool = False,
) -> dict[str, Any]:
    assessment = triage(symptoms, age=age, pregnancy=pregnancy)
    return recommend_medications(
        symptoms,
        assessment,
        age=age,
        pregnancy=pregnancy,
    )


def summarize_health_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate vitals into the same overview used by the product UI."""
    return health_overview(records or [])


def correlate_symptoms_and_vitals(
    records: list[dict[str, Any]],
    conversations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Find date-aligned patterns between consultation topics and vitals."""
    insights = longitudinal_insights(records or [], conversations or [])
    return {"insights": insights, "count": len(insights)}


TOOL_SPECS = [
    {
        "name": "search_medical_entities",
        "description": "混合检索 Neo4j 医疗实体，返回实体类型、匹配方式和相关性。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "中文医疗查询"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "expand_medical_entity",
        "description": "展开指定医疗实体的一跳或二跳关系及证据。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string"},
                "name": {"type": "string"},
                "depth": {"type": "integer", "minimum": 1, "maximum": 2},
            },
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "assess_symptoms",
        "description": "根据症状和个人基本信息进行风险分级，不提供确定诊断。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symptoms": {"type": "string"},
                "duration_days": {"type": "integer"},
                "age": {"type": "integer"},
                "pregnancy": {"type": "boolean"},
            },
            "required": ["symptoms"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "medication_options",
        "description": "按症状和人群禁忌匹配非处方对症参考，不提供处方剂量。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symptoms": {"type": "string"},
                "age": {"type": "integer"},
                "pregnancy": {"type": "boolean"},
            },
            "required": ["symptoms"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "summarize_health_metrics",
        "description": "汇总多条健康记录，输出评分、趋势、异常指标与提示。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "description": "健康记录数组，字段同 /api/health/records",
                    "items": {"type": "object"},
                }
            },
            "required": ["records"],
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "correlate_symptoms_and_vitals",
        "description": "按日期对齐咨询主题与体征，返回可能的纵向关联模式。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records": {"type": "array", "items": {"type": "object"}},
                "conversations": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["records", "conversations"],
        },
        "annotations": {"readOnlyHint": True},
    },
]

TOOL_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "search_medical_entities": search_medical_entities,
    "expand_medical_entity": expand_medical_entity,
    "assess_symptoms": assess_symptoms,
    "medication_options": medication_options,
    "summarize_health_metrics": summarize_health_metrics,
    "correlate_symptoms_and_vitals": correlate_symptoms_and_vitals,
}


def call_tool(name: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], float]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        raise ValueError(f"unknown tool: {name}")
    started = time.perf_counter()
    result = handler(**arguments)
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    return result, elapsed

