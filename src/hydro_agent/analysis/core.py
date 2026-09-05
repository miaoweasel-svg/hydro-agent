"""Explainable statistics, trends, correlation, and gate-change analysis."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

METRICS = ("upstream_level", "downstream_level", "gate_opening", "flow")
METRIC_LABELS = {
    "upstream_level": "上游水位",
    "downstream_level": "下游水位",
    "gate_opening": "闸门开度",
    "flow": "流量",
}
METRIC_UNITS = {
    "upstream_level": "m",
    "downstream_level": "m",
    "gate_opening": "%",
    "flow": "m³/s",
}


def _validate_metrics(metrics: Iterable[str] | None) -> list[str]:
    selected = list(metrics or METRICS)
    invalid = [metric for metric in selected if metric not in METRICS]
    if invalid:
        raise ValueError(f"不支持的指标: {', '.join(invalid)}")
    return selected


def filter_time_range(
    frame: pd.DataFrame, start_time: str | None = None, end_time: str | None = None
) -> pd.DataFrame:
    """Return rows inside an inclusive time range."""

    selected = frame
    if start_time:
        selected = selected[selected["timestamp"] >= pd.Timestamp(start_time)]
    if end_time:
        selected = selected[selected["timestamp"] <= pd.Timestamp(end_time)]
    if selected.empty:
        raise ValueError("所选时间范围内没有数据。")
    return selected.copy()


def _iso(timestamp: Any) -> str:
    return pd.Timestamp(timestamp).isoformat()


def get_statistics(
    frame: pd.DataFrame,
    metrics: Iterable[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """Calculate descriptive statistics using Pandas, never an LLM."""

    selected = filter_time_range(frame, start_time, end_time)
    result: dict[str, Any] = {
        "row_count": int(len(selected)),
        "start_time": _iso(selected["timestamp"].iloc[0]),
        "end_time": _iso(selected["timestamp"].iloc[-1]),
        "metrics": {},
    }
    for metric in _validate_metrics(metrics):
        series = selected[metric]
        result["metrics"][metric] = {
            "label": METRIC_LABELS[metric],
            "unit": METRIC_UNITS[metric],
            "mean": round(float(series.mean()), 4),
            "min": round(float(series.min()), 4),
            "min_time": _iso(selected.loc[series.idxmin(), "timestamp"]),
            "max": round(float(series.max()), 4),
            "max_time": _iso(selected.loc[series.idxmax(), "timestamp"]),
            "std": round(float(series.std(ddof=0)), 4),
        }
    return result


def analyze_trend(
    frame: pd.DataFrame,
    metrics: Iterable[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """Estimate each metric's linear slope and total change over the time range."""

    selected = filter_time_range(frame, start_time, end_time)
    elapsed_hours = (
        selected["timestamp"] - selected["timestamp"].iloc[0]
    ).dt.total_seconds() / 3600
    result: dict[str, Any] = {
        "start_time": _iso(selected["timestamp"].iloc[0]),
        "end_time": _iso(selected["timestamp"].iloc[-1]),
        "point_count": int(len(selected)),
        "trends": {},
    }
    for metric in _validate_metrics(metrics):
        values = selected[metric].to_numpy(dtype=float)
        slope = float(np.polyfit(elapsed_hours, values, 1)[0]) if len(values) > 1 else 0.0
        change = float(values[-1] - values[0])
        scale = max(float(np.std(values)), 1e-9)
        if abs(change) < 0.2 * scale:
            direction = "基本稳定"
        elif change > 0:
            direction = "上升"
        else:
            direction = "下降"
        result["trends"][metric] = {
            "label": METRIC_LABELS[metric],
            "unit": METRIC_UNITS[metric],
            "start_value": round(float(values[0]), 4),
            "end_value": round(float(values[-1]), 4),
            "change": round(change, 4),
            "slope_per_hour": round(slope, 6),
            "direction": direction,
        }
    return result


def calculate_correlation(
    frame: pd.DataFrame,
    metrics: Iterable[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """Calculate a Pearson correlation matrix for selected operation variables."""

    selected = filter_time_range(frame, start_time, end_time)
    columns = _validate_metrics(metrics)
    if len(columns) < 2:
        raise ValueError("相关性分析至少需要两个指标。")
    matrix = selected[columns].corr(method="pearson")
    pairs: list[dict[str, Any]] = []
    for left_index, left in enumerate(columns):
        for right in columns[left_index + 1 :]:
            value = float(matrix.loc[left, right])
            strength = "强" if abs(value) >= 0.7 else "中等" if abs(value) >= 0.4 else "弱"
            pairs.append(
                {
                    "left": left,
                    "right": right,
                    "coefficient": round(value, 4),
                    "interpretation": f"{strength}{'正' if value >= 0 else '负'}相关",
                }
            )
    return {
        "method": "Pearson",
        "row_count": int(len(selected)),
        "matrix": matrix.round(4).to_dict(),
        "pairs": sorted(pairs, key=lambda item: abs(item["coefficient"]), reverse=True),
    }


def find_gate_changes(
    frame: pd.DataFrame,
    top_n: int = 3,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """Find the largest consecutive gate-opening changes."""

    selected = filter_time_range(frame, start_time, end_time).reset_index(drop=True)
    if not 1 <= top_n <= 20:
        raise ValueError("top_n 必须位于 1 到 20 之间。")
    differences = selected["gate_opening"].diff()
    ranked = differences.abs().nlargest(min(top_n, max(len(selected) - 1, 0))).index
    changes = []
    for index in ranked:
        changes.append(
            {
                "start_time": _iso(selected.loc[index - 1, "timestamp"]),
                "end_time": _iso(selected.loc[index, "timestamp"]),
                "from_opening": round(float(selected.loc[index - 1, "gate_opening"]), 3),
                "to_opening": round(float(selected.loc[index, "gate_opening"]), 3),
                "change": round(float(differences.loc[index]), 3),
                "absolute_change": round(abs(float(differences.loc[index])), 3),
                "unit": "%",
            }
        )
    return {"top_n": len(changes), "changes": changes}

