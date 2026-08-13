"""Tests for deterministic input generation and validation."""

import pandas as pd
import pytest

from hungary2050.data import DataValidationError, generate_synthetic_profiles, validate_profiles


def test_synthetic_profiles_are_deterministic_and_valid() -> None:
    first = generate_synthetic_profiles()
    second = generate_synthetic_profiles()
    pd.testing.assert_frame_equal(first, second)
    validated = validate_profiles(first, expected_hours=8760)
    assert validated["demand_mw"].mean() == pytest.approx(7500.0, rel=1e-5)
    assert validated["solar_capacity_factor"].between(0, 1).all()
    assert validated["wind_capacity_factor"].between(0, 1).all()


def test_validation_rejects_out_of_range_capacity_factor() -> None:
    profiles = generate_synthetic_profiles().head(24)
    profiles.loc[3, "solar_capacity_factor"] = 1.1
    with pytest.raises(DataValidationError, match="between 0 and 1"):
        validate_profiles(profiles)


def test_validation_rejects_missing_hour() -> None:
    profiles = generate_synthetic_profiles().head(24).drop(index=8)
    with pytest.raises(DataValidationError, match="consecutive hourly"):
        validate_profiles(profiles)

