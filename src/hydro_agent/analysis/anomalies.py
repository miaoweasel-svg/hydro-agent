"""Simple, transparent anomaly detection methods for operation data."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from hydro_agent.analysis.core import (
    METRIC_LABELS,
    METRIC_UNITS,
    _iso,
    _validate_metrics,
    filter_time_range,
)


def _zscore(series: pd.Series, threshold: float) -> tuple[pd.Series, pd.Series, str]:
    std = float(series.std(ddof=0))
    scores = (series - series.mean()).abs() / std if std else pd.Series(0.0, index=series.index)
    return scores >= threshold, scores, f"全局 Z-score ≥ {threshold:g}"


def _iqr(series: pd.Series, threshold: float) -> tuple[pd.Series, pd.Series, str]:
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = float(q3 - q1)
    if iqr == 0:
        scores = pd.Series(0.0, index=series.index)
        return scores.astype(bool), scores, f"IQR 边界系数 {threshold:g}"
    lower, upper = q1 - threshold * iqr, q3 + threshold * iqr
    outside = (series < lower) | (series > upper)
    scores = pd.concat([(lower - series) / iqr, (series - upper) / iqr], axis=1).max(axis=1).clip(lower=0)
    return outside, scores, f"超出 [{lower:.3f}, {upper:.3f}]"


def _rolling(series: pd.Series, threshold: float) -> tuple[pd.Series, pd.Series, str]:
    baseline = series.rolling(24, center=True, min_periods=8).median()
    residual = (series - baseline).abs()
    scale = residual.rolling(48, center=True, min_periods=12).median() * 1.4826
    fallback = max(float(residual.median() * 1.4826), 1e-9)
    scores = residual / scale.fillna(fallback).clip(lower=fallback / 10)
    return scores >= threshold, scores, f"24小时滚动中位数偏差分数 ≥ {threshold:g}"


def detect_anomalies(
    frame: pd.DataFrame,
    metrics: Iterable[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    method: str = "zscore",
    threshold: float = 3.0,
) -> dict[str, Any]:
    """Detect anomalies and return timestamps, values, scores, and criteria."""

    selected = filter_time_range(frame, start_time, end_time)
    detectors = {"zscore": _zscore, "iqr": _iqr, "rolling": _rolling}
    if method not in detectors:
        raise ValueError("method 必须是 zscore、iqr 或 rolling。")
    if threshold <= 0:
        raise ValueError("threshold 必须大于 0。")

    anomalies: list[dict[str, Any]] = []
    for metric in _validate_metrics(metrics):
        mask, scores, criterion = detectors[method](selected[metric], threshold)
        for index in selected.index[mask.fillna(False)]:
            anomalies.append(
                {
                    "timestamp": _iso(selected.loc[index, "timestamp"]),
                    "variable": metric,
                    "label": METRIC_LABELS[metric],
                    "actual_value": round(float(selected.loc[index, metric]), 4),
                    "unit": METRIC_UNITS[metric],
                    "anomaly_score": round(float(scores.loc[index]), 3),
                    "criterion": criterion,
                }
            )
    anomalies.sort(key=lambda item: (item["timestamp"], item["variable"]))
    return {
        "method": method,
        "threshold": threshold,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "note": "异常仅表示统计偏离，需结合工程背景人工复核。",
    }

