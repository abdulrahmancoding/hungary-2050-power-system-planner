"""Tests for YAML scenario loading and validation."""

from pathlib import Path

import pytest

from hungary2050.config import ConfigurationError, discover_scenarios, load_scenario


def test_all_six_scenarios_load(project_root: Path) -> None:
    paths = discover_scenarios(project_root / "scenarios")
    scenarios = [load_scenario(path, project_root / "scenarios" / "base.yaml") for path in paths]
    assert len(scenarios) == 6
    assert len({scenario.slug for scenario in scenarios}) == 6


def test_scenario_override_is_deep_merged(project_root: Path) -> None:
    scenario = load_scenario(
        project_root / "scenarios" / "06_limited_imports.yaml",
        project_root / "scenarios" / "base.yaml",
    )
    imports = scenario.settings["technologies"]["imports"]
    assert imports["existing_capacity_mw"] == 1000
    assert imports["marginal_cost_eur_per_mwh"] == 90


def test_invalid_configuration_is_rejected(tmp_path: Path, project_root: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        "scenario:\n  name: Invalid\n  slug: invalid\n  description: bad\n"
        "model:\n  demand_multiplier: -1\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="demand_multiplier"):
        load_scenario(invalid, project_root / "scenarios" / "base.yaml")

