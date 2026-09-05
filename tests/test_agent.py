from __future__ import annotations

from typing import Any

from hydro_agent.agent import HydroAnalysisAgent, route_question
from hydro_agent.rag import RAGService


def test_eval_questions_route_to_expected_tools(demo_frame):
    questions = {
        "统计8月2日平均上游水位。": "get_statistics",
        "检测异常水位。": "detect_anomalies",
        "根据运行规程说明需要关注哪些指标。": "retrieve_knowledge",
    }

    for question, expected_tool in questions.items():
        names = [name for name, _ in route_question(question, demo_frame)]
        assert expected_tool in names


def test_date_question_passes_filtered_range_to_tool(demo_frame):
    rag = RAGService()
    agent = HydroAnalysisAgent(demo_frame, rag)

    response = agent.ask("统计8月2日平均上游水位。")

    assert response.tool_calls[0].name == "get_statistics"
    assert response.tool_calls[0].result["row_count"] == 24


def test_registry_contains_all_required_tools(demo_frame):
    agent = HydroAnalysisAgent(demo_frame, RAGService())

    assert set(agent.registry.names) == {
        "get_statistics",
        "analyze_trend",
        "detect_anomalies",
        "calculate_correlation",
        "find_gate_changes",
        "retrieve_knowledge",
        "generate_operation_report",
    }


class FakeToolCallingProvider:
    def run(self, question, system_prompt, tools, execute_tool):
        del question, system_prompt
        names = {tool["name"] for tool in tools}
        assert "detect_anomalies" in names
        arguments: dict[str, Any] = {
            "metrics": ["upstream_level"],
            "start_time": None,
            "end_time": None,
            "method": "zscore",
            "threshold": 3.0,
        }
        result = execute_tool("detect_anomalies", arguments)
        return "已通过工具完成异常检测。", [("detect_anomalies", arguments, result)]


def test_agent_executes_provider_tool_calls_without_real_api(demo_frame):
    agent = HydroAnalysisAgent(demo_frame, RAGService(), FakeToolCallingProvider())

    response = agent.ask("请检测上游水位异常")

    assert response.mode == "openai"
    assert response.tool_calls[0].name == "detect_anomalies"
    assert response.tool_calls[0].result["anomaly_count"] >= 2
