from __future__ import annotations

import pandas as pd

from hydro_agent.analysis import (
    calculate_correlation,
    detect_anomalies,
    find_gate_changes,
    get_statistics,
)


def test_statistics_respects_date_filter(demo_frame):
    result = get_statistics(
        demo_frame,
        metrics=["upstream_level"],
        start_time="2026-08-02T00:00:00",
        end_time="2026-08-02T23:59:59",
    )

    expected = demo_frame.iloc[24:48]["upstream_level"].mean()
    assert result["row_count"] == 24
    assert result["metrics"]["upstream_level"]["mean"] == round(float(expected), 4)


def test_zscore_detects_all_five_injected_anomalies(demo_frame):
    result = detect_anomalies(
        demo_frame,
        metrics=["upstream_level", "downstream_level", "flow"],
        method="zscore",
        threshold=3.0,
    )
    detected = {
        (pd.Timestamp(item["timestamp"]), item["variable"]) for item in result["anomalies"]
    }
    expected = {
        (demo_frame.loc[55, "timestamp"], "upstream_level"),
        (demo_frame.loc[148, "timestamp"], "downstream_level"),
        (demo_frame.loc[269, "timestamp"], "upstream_level"),
        (demo_frame.loc[101, "timestamp"], "flow"),
        (demo_frame.loc[302, "timestamp"], "flow"),
    }

    assert expected <= detected


def test_correlation_returns_symmetric_matrix(demo_frame):
    result = calculate_correlation(demo_frame, ["gate_opening", "flow"])

    left = result["matrix"]["flow"]["gate_opening"]
    right = result["matrix"]["gate_opening"]["flow"]
    assert left == right
    assert left > 0.8


def test_gate_changes_returns_largest_adjustments(demo_frame):
    result = find_gate_changes(demo_frame, top_n=3)

    assert len(result["changes"]) == 3
    assert result["changes"][0]["absolute_change"] >= result["changes"][1]["absolute_change"]
    transition_hours = {144, 216, 264}
    returned_hours = {
        int((pd.Timestamp(item["end_time"]) - demo_frame.loc[0, "timestamp"]).total_seconds() / 3600)
        for item in result["changes"]
    }
    assert len(returned_hours & transition_hours) >= 2

