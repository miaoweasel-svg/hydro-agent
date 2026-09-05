"""Tool definitions and deterministic handler registration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from hydro_agent.analysis.anomalies import detect_anomalies
from hydro_agent.analysis.core import (
    analyze_trend,
    calculate_correlation,
    find_gate_changes,
    get_statistics,
)
from hydro_agent.analysis.report import generate_operation_report
from hydro_agent.rag.service import RAGService

ToolHandler = Callable[..., dict[str, Any]]


def _nullable_string(description: str) -> dict[str, Any]:
    return {"type": ["string", "null"], "description": description}


def _object_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "strict": True,
        }


class ToolRegistry:
    """Expose the seven project tools without coupling them to an LLM SDK."""

    def __init__(self, frame: pd.DataFrame, rag_service: RAGService) -> None:
        metric_property = {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["upstream_level", "downstream_level", "gate_opening", "flow"],
            },
            "description": "待分析指标；空数组表示全部指标。",
        }
        time_properties = {
            "start_time": _nullable_string("ISO 格式起始时间；无筛选时为 null。"),
            "end_time": _nullable_string("ISO 格式结束时间；无筛选时为 null。"),
        }
        self._tools: dict[str, ToolSpec] = {}
        self._register(
            ToolSpec(
                "get_statistics",
                "计算指定时段和指标的均值、极值、标准差；数值问题必须调用。",
                _object_schema({"metrics": metric_property, **time_properties}),
                lambda **kwargs: get_statistics(frame, **kwargs),
            )
        )
        self._register(
            ToolSpec(
                "analyze_trend",
                "计算指定时段内变量的首尾变化、方向和每小时线性斜率。",
                _object_schema({"metrics": metric_property, **time_properties}),
                lambda **kwargs: analyze_trend(frame, **kwargs),
            )
        )
        self._register(
            ToolSpec(
                "detect_anomalies",
                "使用 Z-score、IQR 或滚动统计检测异常，返回时间、变量、数值和依据。",
                _object_schema(
                    {
                        "metrics": metric_property,
                        **time_properties,
                        "method": {"type": "string", "enum": ["zscore", "iqr", "rolling"]},
                        "threshold": {"type": "number", "exclusiveMinimum": 0},
                    }
                ),
                lambda **kwargs: detect_anomalies(frame, **kwargs),
            )
        )
        self._register(
            ToolSpec(
                "calculate_correlation",
                "使用 Python 计算两个或更多运行变量的 Pearson 相关性。",
                _object_schema({"metrics": metric_property, **time_properties}),
                lambda **kwargs: calculate_correlation(frame, **kwargs),
            )
        )
        self._register(
            ToolSpec(
                "find_gate_changes",
                "查找相邻采样点之间闸门开度绝对变化最大的时段。",
                _object_schema(
                    {
                        "top_n": {"type": "integer", "minimum": 1, "maximum": 20},
                        **time_properties,
                    }
                ),
                lambda **kwargs: find_gate_changes(frame, **kwargs),
            )
        )
        self._register(
            ToolSpec(
                "retrieve_knowledge",
                "从本地工程知识库检索可追溯的相关片段；规程问题必须调用。",
                _object_schema(
                    {
                        "query": {"type": "string", "minLength": 1},
                        "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
                    }
                ),
                lambda query, top_k: {
                    "query": query,
                    "results": [item.to_dict() for item in rag_service.search(query, top_k)],
                    "note": "检索片段仅供演示分析，引用结论需回到原文复核。",
                },
            )
        )
        self._register(
            ToolSpec(
                "generate_operation_report",
                "用 Python 统计结果生成指定时段的运行情况 Markdown 报告。",
                _object_schema(time_properties),
                lambda **kwargs: generate_operation_report(frame, **kwargs),
            )
        )

    def _register(self, tool: ToolSpec) -> None:
        self._tools[tool.name] = tool

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.openai_schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self._tools:
            raise KeyError(f"未知工具: {name}")
        return self._tools[name].handler(**arguments)

