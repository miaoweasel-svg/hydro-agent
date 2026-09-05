"""Deterministic offline question router used when no API key is configured."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

METRIC_TERMS = {
    "upstream_level": ("上游水位", "上游"),
    "downstream_level": ("下游水位", "下游"),
    "gate_opening": ("闸门开度", "闸门", "开度"),
    "flow": ("流量",),
}
ONE_DAY = pd.Timedelta(1, unit="D")
ONE_MICROSECOND = pd.Timedelta(1, unit="us")


def _extract_metrics(question: str) -> list[str]:
    metrics = [
        metric for metric, terms in METRIC_TERMS.items() if any(term in question for term in terms)
    ]
    if "水位" in question and not any(
        metric in metrics for metric in ("upstream_level", "downstream_level")
    ):
        metrics.extend(["upstream_level", "downstream_level"])
    return metrics


def _date_arguments(question: str, frame: pd.DataFrame) -> dict[str, str | None]:
    default_year = int(frame["timestamp"].dt.year.mode().iloc[0])
    range_match = re.search(
        r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日\s*(?:至|到|—|~|-)\s*"
        r"(?:(\d{4})年)?(?:(\d{1,2})月)?(\d{1,2})日",
        question,
    )
    if range_match:
        y1, m1, d1, y2, m2, d2 = range_match.groups()
        start = pd.Timestamp(year=int(y1 or default_year), month=int(m1), day=int(d1))
        end = pd.Timestamp(
            year=int(y2 or y1 or default_year), month=int(m2 or m1), day=int(d2)
        ) + ONE_DAY - ONE_MICROSECOND
        return {"start_time": start.isoformat(), "end_time": end.isoformat()}

    iso_dates = re.findall(r"\d{4}-\d{1,2}-\d{1,2}", question)
    if iso_dates:
        start = pd.Timestamp(iso_dates[0])
        end_date = pd.Timestamp(iso_dates[-1])
        end = end_date + ONE_DAY - ONE_MICROSECOND
        return {"start_time": start.isoformat(), "end_time": end.isoformat()}

    single = re.search(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日", question)
    if single:
        year, month, day = single.groups()
        start = pd.Timestamp(year=int(year or default_year), month=int(month), day=int(day))
        end = start + ONE_DAY - ONE_MICROSECOND
        return {"start_time": start.isoformat(), "end_time": end.isoformat()}
    return {"start_time": None, "end_time": None}


def _top_n(question: str) -> int:
    match = re.search(r"(?:最大|前)\s*(\d+)\s*(?:个|段|次)?", question)
    if match:
        return min(max(int(match.group(1)), 1), 20)
    chinese = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5}
    match = re.search(r"(?:最大|前)\s*([一二两三四五])\s*(?:个|段|次)?", question)
    return chinese.get(match.group(1), 3) if match else 3


def route_question(question: str, frame: pd.DataFrame) -> list[tuple[str, dict[str, Any]]]:
    """Map common Chinese demo questions to one or more explainable tools."""

    metrics = _extract_metrics(question)
    dates = _date_arguments(question, frame)
    calls: list[tuple[str, dict[str, Any]]] = []

    if any(term in question for term in ("日报", "运行报告", "生成报告")):
        return [("generate_operation_report", dates)]

    if any(term in question for term in ("规程", "知识库", "根据", "规范", "关注哪些指标")):
        calls.append(("retrieve_knowledge", {"query": question, "top_k": 3}))
        if "异常" in question:
            calls.insert(
                0,
                (
                    "detect_anomalies",
                    {"metrics": metrics, **dates, "method": "zscore", "threshold": 3.0},
                ),
            )
        return calls

    if "异常" in question:
        return [
            (
                "detect_anomalies",
                {"metrics": metrics, **dates, "method": "zscore", "threshold": 3.0},
            )
        ]

    if any(term in question for term in ("相关", "关系", "关联")):
        correlation_metrics = metrics if len(metrics) >= 2 else []
        return [("calculate_correlation", {"metrics": correlation_metrics, **dates})]

    if any(term in question for term in ("闸门", "开度")) and any(
        term in question for term in ("变化最大", "调整", "变动最大")
    ):
        return [("find_gate_changes", {"top_n": _top_n(question), **dates})]

    if any(term in question for term in ("趋势", "变化", "走势", "分析")):
        return [("analyze_trend", {"metrics": metrics, **dates})]

    if any(term in question for term in ("统计", "平均", "最大", "最小", "极值")):
        return [("get_statistics", {"metrics": metrics, **dates})]

    return [("get_statistics", {"metrics": metrics, **dates})]
