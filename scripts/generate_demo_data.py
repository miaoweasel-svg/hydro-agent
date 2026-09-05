"""Generate deterministic 14-day synthetic gate-operation data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def build_demo_data(seed: int = 2027) -> pd.DataFrame:
    """Create hourly simulated data with five labelled injected anomalies."""

    rng = np.random.default_rng(seed)
    periods = 14 * 24
    hours = np.arange(periods)
    timestamp = pd.date_range("2026-08-01", periods=periods, freq="h")

    upstream = 8.25 + 0.16 * np.sin(2 * np.pi * hours / 24) + 0.04 * np.sin(
        2 * np.pi * hours / (24 * 7)
    ) + rng.normal(0, 0.018, periods)
    downstream = 5.10 + 0.09 * np.sin(2 * np.pi * (hours - 3) / 24) + rng.normal(
        0, 0.015, periods
    )

    gate = np.full(periods, 35.0)
    gate[36:72] = 48.0
    gate[72:144] = 32.0
    gate[144:216] = 58.0
    gate[216:264] = 42.0
    gate[264:] = 52.0
    gate += 1.1 * np.sin(2 * np.pi * hours / 12) + rng.normal(0, 0.25, periods)

    flow = 0.95 * gate + 19.0 * (upstream - downstream) + rng.normal(0, 1.3, periods)
    notes = np.full(periods, "", dtype=object)
    injected = np.zeros(periods, dtype=bool)

    anomaly_specs = {
        55: ("upstream", 1.20, "预设上游水位高值异常"),
        148: ("downstream", -0.75, "预设下游水位低值异常"),
        269: ("upstream", -1.05, "预设上游水位低值异常"),
        101: ("flow", 65.0, "预设流量高值异常"),
        302: ("flow", -55.0, "预设流量低值异常"),
    }
    for index, (target, amount, note) in anomaly_specs.items():
        if target == "upstream":
            upstream[index] += amount
        elif target == "downstream":
            downstream[index] += amount
        else:
            flow[index] += amount
        injected[index] = True
        notes[index] = note

    return pd.DataFrame(
        {
            "timestamp": timestamp,
            "upstream_level": upstream.round(3),
            "downstream_level": downstream.round(3),
            "gate_opening": gate.round(2),
            "flow": flow.round(3),
            "is_injected_anomaly": injected,
            "anomaly_note": notes,
            "data_origin": "synthetic",
        }
    )


if __name__ == "__main__":
    output = Path(__file__).resolve().parents[1] / "data" / "synthetic_gate_operation.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    build_demo_data().to_csv(output, index=False, encoding="utf-8-sig")
    print(f"Generated {output} with {14 * 24} hourly rows.")
