from __future__ import annotations

import pandas as pd
import pytest

from scripts.generate_demo_data import build_demo_data


@pytest.fixture
def demo_frame() -> pd.DataFrame:
    return build_demo_data()

