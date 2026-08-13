"""Deterministic demonstration-data generation and validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"timestamp", "demand_mw", "solar_capacity_factor", "wind_capacity_factor"}


class DataValidationError(ValueError):
    """Raised when hourly model inputs fail validation."""


def generate_synthetic_profiles(year: int = 2021) -> pd.DataFrame:
    """Create a deterministic 8,760-hour load, solar, and wind demonstration year.

    The functions reproduce seasonal, diurnal, weekly, and multi-day variability.
    They are modelling constructs—not observations or forecasts.
    """

    index = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", inclusive="left")
    if len(index) != 8760:
        raise ValueError("Choose a non-leap year for the 8,760-hour demonstration dataset")

    hour = index.hour.to_numpy()
    day = index.dayofyear.to_numpy()
    weekday = index.dayofweek.to_numpy()

    # Synthetic demand: 7.5 GW mean, winter-led seasonality, morning/evening peaks,
    # a small weekday uplift, and deterministic intra-week variation.
    winter = 0.12 * np.cos(2 * np.pi * (day - 15) / 365.0)
    evening_peak = 0.13 * np.exp(-0.5 * ((hour - 19) / 2.4) ** 2)
    morning_peak = 0.06 * np.exp(-0.5 * ((hour - 8) / 2.8) ** 2)
    overnight_dip = -0.10 * np.exp(-0.5 * ((hour - 3) / 2.7) ** 2)
    weekday_effect = np.where(weekday < 5, 0.025, -0.035)
    deterministic_texture = 0.025 * np.sin(2 * np.pi * np.arange(len(index)) / (24 * 9))
    demand_shape = 1 + winter + evening_peak + morning_peak + overnight_dip + weekday_effect
    demand_shape += deterministic_texture
    demand_mw = 7500.0 * demand_shape / demand_shape.mean()

    # Synthetic solar: astronomical-style daylight envelope plus slow, repeatable
    # cloud modulation. Zero at night and bounded by one.
    daylight_hours = 12.0 + 4.0 * np.sin(2 * np.pi * (day - 80) / 365.0)
    solar_noon = 12.0
    phase = (hour - (solar_noon - daylight_hours / 2)) / daylight_hours
    daylight = np.where((phase >= 0) & (phase <= 1), np.sin(np.pi * phase), 0.0)
    seasonal_irradiance = 0.72 + 0.23 * np.sin(2 * np.pi * (day - 80) / 365.0)
    cloud = 0.78 + 0.16 * np.sin(2 * np.pi * day / 11.0) + 0.06 * np.cos(2 * np.pi * day / 4.7)
    solar_cf = np.clip(daylight**1.45 * seasonal_irradiance * cloud, 0, 1)

    # Synthetic wind: winter-biased, multi-day systems and shorter deterministic
    # fluctuations. It is an illustrative capacity factor, not weather reanalysis.
    wind_cf = (
        0.31
        + 0.08 * np.cos(2 * np.pi * (day - 20) / 365.0)
        + 0.13 * np.sin(2 * np.pi * np.arange(len(index)) / (24 * 6.5))
        + 0.07 * np.cos(2 * np.pi * np.arange(len(index)) / (24 * 2.3))
        + 0.035 * np.sin(2 * np.pi * np.arange(len(index)) / 17.0)
    )
    wind_cf = np.clip(wind_cf, 0.03, 0.78)

    return pd.DataFrame(
        {
            "timestamp": index,
            "demand_mw": demand_mw.round(3),
            "solar_capacity_factor": solar_cf.round(6),
            "wind_capacity_factor": wind_cf.round(6),
        }
    )


def validate_profiles(frame: pd.DataFrame, expected_hours: int | None = None) -> pd.DataFrame:
    """Validate hourly profiles and return a timestamp-indexed copy."""

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise DataValidationError(f"Missing input columns: {sorted(missing)}")

    validated = frame.copy()
    try:
        validated["timestamp"] = pd.to_datetime(validated["timestamp"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise DataValidationError("timestamp contains invalid datetimes") from exc
    if validated["timestamp"].duplicated().any():
        raise DataValidationError("timestamp values must be unique")
    validated = validated.sort_values("timestamp").set_index("timestamp")
    if not validated.index.is_monotonic_increasing:
        raise DataValidationError("timestamps must be increasing")
    if len(validated) > 1:
        intervals = validated.index.to_series().diff().dropna()
        if not (intervals == pd.Timedelta(hours=1)).all():
            raise DataValidationError("input must have consecutive hourly timestamps")
    if expected_hours is not None and len(validated) != expected_hours:
        raise DataValidationError(f"Expected {expected_hours} rows, found {len(validated)}")
    if validated.isna().any().any():
        raise DataValidationError("input profiles cannot contain missing values")
    if (validated["demand_mw"] <= 0).any():
        raise DataValidationError("demand_mw must be positive")
    for column in ("solar_capacity_factor", "wind_capacity_factor"):
        if not validated[column].between(0, 1).all():
            raise DataValidationError(f"{column} must be between 0 and 1")
    return validated


def prepare_data(output_path: str | Path, year: int = 2021) -> Path:
    """Generate, validate, and save the deterministic demonstration dataset."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = generate_synthetic_profiles(year)
    validate_profiles(frame, expected_hours=8760)
    frame.to_csv(output, index=False, lineterminator="\n")
    return output


def load_profiles(path: str | Path, hours: int | None = None) -> pd.DataFrame:
    """Load and validate a processed profile CSV, optionally truncating for tests."""

    frame = pd.read_csv(path)
    if hours is not None:
        if hours <= 0:
            raise DataValidationError("hours must be positive")
        frame = frame.head(hours)
    return validate_profiles(frame, expected_hours=hours)

