from __future__ import annotations

import pytest

from hydro_agent.analysis.data_loader import DataValidationError, load_operation_data


def test_load_csv_bytes_normalizes_timestamp(demo_frame):
    loaded = load_operation_data(
        demo_frame.to_csv(index=False).encode("utf-8"), "operation.csv"
    )

    assert len(loaded) == 336
    assert str(loaded["timestamp"].dtype).startswith("datetime64")
    assert loaded["data_origin"].eq("synthetic").all()


def test_missing_required_column_is_rejected(demo_frame):
    invalid = demo_frame.drop(columns=["flow"])

    with pytest.raises(DataValidationError, match="flow"):
        load_operation_data(invalid.to_csv(index=False).encode(), "invalid.csv")

