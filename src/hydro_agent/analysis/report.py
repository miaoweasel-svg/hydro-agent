"""Deterministic operation report generation from Python tool outputs."""

from __future__ import annotations

from typing import Any

import pandas as pd

from hydro_agent.analysis.anomalies import detect_anomalies
from hydro_agent.analysis.core import find_gate_changes, get_statistics


def generate_operation_report(
    frame: pd.DataFrame,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """Build a traceable Markdown report from deterministic analysis results."""

    stats = get_statistics(frame, start_time=start_time, end_time=end_time)
    anomalies = detect_anomalies(frame, start_time=start_time, end_time=end_time)
    gate_changes = find_gate_changes(frame, top_n=3, start_time=start_time, end_time=end_time)
    metric_lines = []
    for item in stats["metrics"].values():
        metric_lines.append(
            f"- {item['label']}：平均 {item['mean']:.3f} {item['unit']}，"
            f"范围 {item['min']:.3f}–{item['max']:.3f} {item['unit']}"
        )
    anomaly_lines = [
        f"- {item['timestamp']}，{item['label']} {item['actual_value']} {item['unit']}，"
        f"分数 {item['anomaly_score']}（{item['criterion']}）"
        for item in anomalies["anomalies"][:10]
    ] or ["- 本方法在所选数据中未检出统计异常。"]
    gate_lines = [
        f"- {item['end_time']}：{item['from_opening']:.2f}% → "
        f"{item['to_opening']:.2f}%（变化 {item['change']:+.2f} 个百分点）"
        for item in gate_changes["changes"]
    ]
    markdown = "\n".join(
        [
            "# 水利工程运行情况分析报告（模拟数据）",
            "",
            f"**统计时段：** {stats['start_time']} 至 {stats['end_time']}  " ,
            f"**数据点数：** {stats['row_count']}",
            "",
            "## 核心指标",
            *metric_lines,
            "",
            "## 统计异常",
            *anomaly_lines,
            "",
            "## 主要闸门调整",
            *gate_lines,
            "",
            "## 说明",
            "本报告基于 synthetic/demo 数据和可解释的 Python 统计工具自动生成。",
            "异常提示仅供分析参考，系统不用于真实工程调度或安全决策。",
        ]
    )
    return {
        "markdown": markdown,
        "statistics": stats,
        "anomalies": anomalies,
        "gate_changes": gate_changes,
    }

