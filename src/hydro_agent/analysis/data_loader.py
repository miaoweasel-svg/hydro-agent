"""CSV and Excel loading with schema validation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

REQUIRED_COLUMNS = (
    "timestamp",
    "upstream_level",
    "downstream_level",
    "gate_opening",
    "flow",
)
NUMERIC_COLUMNS = REQUIRED_COLUMNS[1:]


class DataValidationError(ValueError):
    """Raised when uploaded operation data cannot be safely analyzed."""


def _validate_and_normalize(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DataValidationError(f"缺少必需字段: {', '.join(missing)}")

    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce")
    for column in NUMERIC_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    invalid = result[list(REQUIRED_COLUMNS)].isna().any(axis=1)
    if invalid.any():
        rows = ", ".join(str(index + 2) for index in result.index[invalid][:8])
        raise DataValidationError(f"时间或数值字段存在空值/非法值，示例行号: {rows}")
    if result["timestamp"].duplicated().any():
        raise DataValidationError("timestamp 存在重复值，请先去重。")
    if (result["gate_opening"] < 0).any() or (result["gate_opening"] > 100).any():
        raise DataValidationError("gate_opening 必须位于 0 到 100 之间。")

    return result.sort_values("timestamp").reset_index(drop=True)


def load_operation_data(
    source: str | Path | bytes | BinaryIO, filename: str | None = None
) -> pd.DataFrame:
    """Load operation data from a path or uploaded bytes and validate its schema."""

    if isinstance(source, (str, Path)):
        path = Path(source)
        suffix = path.suffix.lower()
        reader_source: str | Path | BytesIO | BinaryIO = path
    else:
        suffix = Path(filename or "data.csv").suffix.lower()
        reader_source = BytesIO(source) if isinstance(source, bytes) else source

    if suffix == ".csv":
        frame = pd.read_csv(reader_source)
    elif suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(reader_source)
    else:
        raise DataValidationError("仅支持 CSV、XLSX 或 XLS 数据文件。")
    return _validate_and_normalize(frame)

