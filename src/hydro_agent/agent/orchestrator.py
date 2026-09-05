"""Tool-calling orchestration with online and offline execution paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from hydro_agent.agent.registry import ToolRegistry
from hydro_agent.agent.routing import route_question
from hydro_agent.llm.base import AgentLLMProvider
from hydro_agent.rag.service import RAGService

SYSTEM_PROMPT = """你是水利工程运行数据分析助手，只处理当前演示数据与知识库。
必须遵守：
1. 统计、趋势、相关性、异常与排序等数值结论必须调用工具，禁止自行心算或估算。
2. 可组合多个工具；不要捏造工具没有返回的数值。
3. 知识性结论必须调用 retrieve_knowledge，并在回答中标注文件名和页码或章节。
4. 明确说明数据为 synthetic/demo；异常为统计提示，不能作为工程安全结论。
5. 系统仅用于数据分析和技术演示，不提供真实调度、控制或安全决策。
回答使用简洁、专业的中文。"""


@dataclass(frozen=True)
class ToolCallRecord:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


@dataclass(frozen=True)
class AgentResponse:
    answer: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    mode: str = "offline"
    warning: str | None = None


class HydroAnalysisAgent:
    """Coordinate question routing, Python tools, retrieval, and answer generation."""

    def __init__(
        self,
        frame: pd.DataFrame,
        rag_service: RAGService,
        llm_provider: AgentLLMProvider | None = None,
    ) -> None:
        self.frame = frame
        self.registry = ToolRegistry(frame, rag_service)
        self.llm_provider = llm_provider

    def ask(self, question: str) -> AgentResponse:
        if not question.strip():
            raise ValueError("问题不能为空。")
        if self.llm_provider is not None:
            try:
                answer, raw_calls = self.llm_provider.run(
                    question,
                    SYSTEM_PROMPT,
                    self.registry.schemas(),
                    self.registry.execute,
                )
                records = [ToolCallRecord(*item) for item in raw_calls]
                if records:
                    return AgentResponse(
                        self._append_retrieval_sources(answer, records), records, mode="openai"
                    )
            except Exception as exc:
                return self._offline_answer(question, warning=f"OpenAI 调用失败，已回退离线路由：{exc}")
        return self._offline_answer(question)

    def _offline_answer(self, question: str, warning: str | None = None) -> AgentResponse:
        records = []
        for name, arguments in route_question(question, self.frame):
            records.append(ToolCallRecord(name, arguments, self.registry.execute(name, arguments)))
        answer = self._format_results(records)
        return AgentResponse(answer, records, mode="offline", warning=warning)

    @staticmethod
    def _append_retrieval_sources(answer: str, records: list[ToolCallRecord]) -> str:
        sources = []
        for record in records:
            if record.name == "retrieve_knowledge":
                for item in record.result.get("results", []):
                    sources.append(
                        f"- `{item['source']}`（{item['location']}）：{item['text'][:120]}…"
                    )
        if not sources:
            return answer
        return f"{answer}\n\n**检索来源**\n\n" + "\n".join(sources)

    @staticmethod
    def _format_results(records: list[ToolCallRecord]) -> str:
        blocks: list[str] = []
        for record in records:
            result = record.result
            if record.name == "get_statistics":
                lines = [
                    f"- {item['label']}：平均 **{item['mean']:.3f} {item['unit']}**；"
                    f"最小 {item['min']:.3f}，最大 {item['max']:.3f}"
                    for item in result["metrics"].values()
                ]
                blocks.append(
                    f"统计时段为 {result['start_time']} 至 {result['end_time']}，"
                    f"共 {result['row_count']} 个数据点。\n\n" + "\n".join(lines)
                )
            elif record.name == "analyze_trend":
                lines = [
                    f"- {item['label']}：{item['direction']}，首尾变化 "
                    f"**{item['change']:+.3f} {item['unit']}**，线性斜率 "
                    f"{item['slope_per_hour']:+.4f} {item['unit']}/h"
                    for item in result["trends"].values()
                ]
                blocks.append("趋势分析结果：\n\n" + "\n".join(lines))
            elif record.name == "detect_anomalies":
                lines = [
                    f"- {item['timestamp']}：{item['label']} **{item['actual_value']} "
                    f"{item['unit']}**，分数 {item['anomaly_score']}（{item['criterion']}）"
                    for item in result["anomalies"][:12]
                ] or ["- 未检出超过当前阈值的统计异常。"]
                blocks.append(
                    f"使用 {result['method']} 方法检出 {result['anomaly_count']} 个异常点：\n\n"
                    + "\n".join(lines)
                    + f"\n\n{result['note']}"
                )
            elif record.name == "calculate_correlation":
                lines = [
                    f"- {item['left']} ↔ {item['right']}：**{item['coefficient']:+.3f}**，"
                    f"{item['interpretation']}"
                    for item in result["pairs"]
                ]
                blocks.append(
                    f"基于 {result['row_count']} 个点的 Pearson 相关性：\n\n" + "\n".join(lines)
                    + "\n\n相关不等于因果，结果仅描述该时段的线性共同变化。"
                )
            elif record.name == "find_gate_changes":
                lines = [
                    f"{index}. {item['end_time']}：{item['from_opening']:.2f}% → "
                    f"{item['to_opening']:.2f}%（{item['change']:+.2f} 个百分点）"
                    for index, item in enumerate(result["changes"], start=1)
                ]
                blocks.append("闸门开度变化最大的时段：\n\n" + "\n".join(lines))
            elif record.name == "retrieve_knowledge":
                lines = [
                    f"- `{item['source']}`（{item['location']}，相似度 {item['score']:.3f}）："
                    f"{item['text'][:220]}"
                    for item in result["results"]
                ] or ["- 知识库暂无可检索内容。"]
                blocks.append(
                    "知识库检索结果（请以原文为准）：\n\n" + "\n".join(lines)
                    + f"\n\n{result['note']}"
                )
            elif record.name == "generate_operation_report":
                blocks.append(result["markdown"])
        blocks.append(
            "> 本系统仅用于 synthetic/demo 数据分析与技术演示，不用于真实工程调度或安全决策。"
        )
        return "\n\n".join(blocks)
