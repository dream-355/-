from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.graph import detect_intent, medical_graph, population_is_relevant
from backend.llm import _cold_assessment_answer, validate_citations
from backend.mcp_server import handle_request
from backend.vector_index import vector_index


class RetrievalTests(unittest.TestCase):
    def test_intent_detection(self) -> None:
        self.assertEqual(detect_intent("这个病吃什么药？"), "treatment")
        self.assertEqual(detect_intent("应该做什么检查？"), "examination")
        self.assertEqual(detect_intent("头晕通常有哪些症状？"), "symptom")
        self.assertEqual(detect_intent("怎么判断自己是否感冒？"), "assessment")

    def test_vector_recall_finds_medical_entity(self) -> None:
        vector_index.warmup()
        results = vector_index.search("体检血红蛋白偏低", 8)
        self.assertTrue(results)
        self.assertTrue(any("血红蛋白" in item["name"] for item in results))
        self.assertGreater(vector_index.stats()["entities"], 10_000)

    def test_unknown_citations_are_removed(self) -> None:
        citations = [
            {
                "id": "E1",
                "subject": "贫血",
                "predicate": "相关检查",
                "object": "血常规",
            }
        ]
        content = "建议结合血常规判断。[E1][E99]"
        validated = validate_citations(content, citations)
        self.assertIn("[E1]", validated)
        self.assertNotIn("[E99]", validated)
        self.assertIn("贫血 — 相关检查 → 血常规", validated)

    def test_existing_reference_section_is_not_duplicated(self) -> None:
        citations = [
            {
                "id": "E1",
                "subject": "缺铁性贫血",
                "predicate": "相关检查",
                "object": "血常规",
            }
        ]
        content = "建议复查血常规。[E1]\n\n**引用依据**\n- [E1] 缺铁性贫血 — 相关检查 → 血常规"
        validated = validate_citations(content, citations)
        self.assertEqual(validated.count("引用依据"), 1)

    def test_population_filter_removes_pediatric_entities_for_adult(self) -> None:
        self.assertFalse(
            population_is_relevant(
                {"object": "小儿多囊肾"},
                age=29,
                gender="女",
            )
        )
        self.assertTrue(
            population_is_relevant(
                {"object": "肾动脉狭窄"},
                age=29,
                gender="女",
            )
        )

    def test_mcp_exposes_medical_tools(self) -> None:
        result = handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        )
        names = {item["name"] for item in result["result"]["tools"]}
        self.assertIn("search_medical_entities", names)
        self.assertIn("expand_medical_entity", names)
        self.assertIn("assess_symptoms", names)
        self.assertIn("summarize_health_metrics", names)
        self.assertIn("correlate_symptoms_and_vitals", names)

    def test_synonym_query_hits_formal_entity(self) -> None:
        vector_index.warmup()
        results = vector_index.search("血压高怎么办", 5)
        self.assertTrue(results)
        self.assertTrue(any("高血压" in item["name"] for item in results))

    def test_hypertension_complications_exclude_pediatric_noise(self) -> None:
        if not medical_graph.health()["online"]:
            self.skipTest("Neo4j is not available")
        context = medical_graph.build_context(
            "高血压并发症有哪些？",
            age=29,
            gender="女",
        )
        self.assertEqual(context["intent"], "complication")
        names = [fact["object"] for fact in context["facts"]]
        self.assertTrue(names)
        self.assertFalse(
            any(
                term in name
                for name in names
                for term in ("小儿", "新生儿", "婴儿", "儿童")
            )
        )
        self.assertTrue(
            all(fact["relation"] == "complication" for fact in context["facts"])
        )

    def test_common_cold_assessment_uses_relevant_entity(self) -> None:
        if not medical_graph.health()["online"]:
            self.skipTest("Neo4j is not available")
        context = medical_graph.build_context(
            "怎么判断自己是否感冒",
            age=29,
            gender="女性",
        )
        self.assertEqual(context["intent"], "assessment")
        self.assertEqual(context["entities"][0]["name"], "普通感冒")
        self.assertIn("咽痛", context["sections"].get("症状与体征", []))
        self.assertFalse(
            any(
                term in entity["name"]
                for entity in context["entities"]
                for term in ("克-雅病", "脑萎缩", "判断力下降")
            )
        )
        answer = _cold_assessment_answer(
            context,
            {"level": "low", "red_flags": []},
            {"allergies": []},
        )["content"]
        self.assertIn("普通感冒", answer)
        self.assertIn("可以这样自查", answer)
        self.assertNotIn("克-雅病", answer)

    def test_assessment_question_words_are_not_treated_as_medical_entities(self) -> None:
        if not medical_graph.health()["online"]:
            self.skipTest("Neo4j is not available")
        context = medical_graph.build_context(
            "我怎么判断我是否扭伤",
            age=29,
            gender="女",
        )
        entity_names = {entity["name"] for entity in context["entities"]}
        self.assertTrue(any("扭伤" in name for name in entity_names))
        self.assertNotIn("判断", entity_names)
        self.assertNotIn("自我否定", entity_names)
        evidence_objects = {fact["object"] for fact in context["facts"]}
        self.assertNotIn("脑萎缩", evidence_objects)
        self.assertFalse(
            any(
                term in name
                for name in evidence_objects
                for term in ("高三综合征", "拖延症", "眼部猪囊尾蚴病")
            )
        )

    def test_contextual_prevention_keeps_topic_without_graph_connection(self) -> None:
        with patch.object(medical_graph, "hybrid_search", return_value=[]):
            context = medical_graph.build_context(
                "怎么判断我是否骨折\n当前追问：怎么避免",
                intent_override="prevention",
            )

        self.assertEqual(context["intent"], "prevention")
        self.assertEqual(context["entities"][0]["name"], "骨折")
        self.assertEqual(context["entities"][0]["type"], "MedicalConcept")


if __name__ == "__main__":
    unittest.main()

