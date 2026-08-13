"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from hungary2050.config import load_scenario
from hungary2050.data import generate_synthetic_profiles, validate_profiles


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def short_profiles() -> pd.DataFrame:
    return validate_profiles(generate_synthetic_profiles().head(48), expected_hours=48)


@pytest.fixture
def baseline_scenario(project_root: Path):
    return load_scenario(
        project_root / "scenarios" / "01_baseline.yaml",
        project_root / "scenarios" / "base.yaml",
    )

