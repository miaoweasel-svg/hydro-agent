"""Deterministic analysis functions used by Agent tools."""

from hydro_agent.analysis.anomalies import detect_anomalies
from hydro_agent.analysis.core import (
    METRIC_LABELS,
    METRIC_UNITS,
    analyze_trend,
    calculate_correlation,
    filter_time_range,
    find_gate_changes,
    get_statistics,
)
from hydro_agent.analysis.data_loader import REQUIRED_COLUMNS, load_operation_data

__all__ = [
    "METRIC_LABELS",
    "METRIC_UNITS",
    "REQUIRED_COLUMNS",
    "analyze_trend",
    "calculate_correlation",
    "detect_anomalies",
    "filter_time_range",
    "find_gate_changes",
    "get_statistics",
    "load_operation_data",
]

