"""Scenario loading and validation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(ValueError):
    """Raised when a model configuration is missing or internally inconsistent."""


@dataclass(frozen=True)
class Scenario:
    """Validated scenario definition and merged model settings."""

    name: str
    slug: str
    description: str
    settings: dict[str, Any]
    source_path: Path


REQUIRED_TECHNOLOGIES = {
    "solar",
    "wind",
    "nuclear",
    "gas",
    "battery",
    "imports",
    "load_shedding",
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge dictionaries without mutating either input."""

    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigurationError(f"Configuration file does not exist: {path}")
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(content, dict):
        raise ConfigurationError(f"Expected a YAML mapping in {path}")
    return content


def load_scenario(path: str | Path, base_path: str | Path | None = None) -> Scenario:
    """Load a scenario YAML file, merge it over the base configuration, and validate it."""

    scenario_path = Path(path)
    raw = _read_yaml(scenario_path)
    resolved_base = Path(base_path) if base_path else scenario_path.parent / "base.yaml"
    base = _read_yaml(resolved_base)

    metadata = raw.pop("scenario", None)
    if not isinstance(metadata, dict):
        raise ConfigurationError(f"{scenario_path} must contain a 'scenario' mapping")
    settings = _deep_merge(base, raw)
    scenario = Scenario(
        name=str(metadata.get("name", "")).strip(),
        slug=str(metadata.get("slug", "")).strip(),
        description=str(metadata.get("description", "")).strip(),
        settings=settings,
        source_path=scenario_path,
    )
    validate_scenario(scenario)
    return scenario


def validate_scenario(scenario: Scenario) -> None:
    """Validate ranges, required fields, and technology definitions."""

    if not scenario.name or not scenario.slug or not scenario.description:
        raise ConfigurationError("Scenario metadata requires name, slug, and description")
    if not scenario.slug.replace("-", "").replace("_", "").isalnum():
        raise ConfigurationError(f"Invalid scenario slug: {scenario.slug!r}")

    settings = scenario.settings
    for section in ("model", "data", "technologies"):
        if section not in settings or not isinstance(settings[section], dict):
            raise ConfigurationError(f"Missing required '{section}' mapping")

    model = settings["model"]
    if float(model.get("demand_multiplier", 0)) <= 0:
        raise ConfigurationError("model.demand_multiplier must be positive")
    for key in ("solar_availability_multiplier", "wind_availability_multiplier"):
        value = float(model.get(key, -1))
        if not 0 <= value <= 1:
            raise ConfigurationError(f"model.{key} must be between 0 and 1")
    emissions_cap = model.get("co2_cap_tonnes")
    if emissions_cap is not None and float(emissions_cap) < 0:
        raise ConfigurationError("model.co2_cap_tonnes cannot be negative")

    technologies = settings["technologies"]
    missing = REQUIRED_TECHNOLOGIES.difference(technologies)
    if missing:
        raise ConfigurationError(f"Missing technology definitions: {sorted(missing)}")

    for name, tech in technologies.items():
        if not isinstance(tech, dict):
            raise ConfigurationError(f"Technology '{name}' must be a mapping")
        for key in ("existing_capacity_mw", "max_capacity_mw", "capital_cost_eur_per_mw_year"):
            if key in tech and float(tech[key]) < 0:
                raise ConfigurationError(f"technologies.{name}.{key} cannot be negative")
        existing = float(tech.get("existing_capacity_mw", 0))
        maximum = float(tech.get("max_capacity_mw", existing))
        if maximum < existing:
            raise ConfigurationError(
                f"technologies.{name}.max_capacity_mw must be >= existing capacity"
            )
        for key in ("efficiency", "efficiency_store", "efficiency_dispatch"):
            if key in tech and not 0 < float(tech[key]) <= 1:
                raise ConfigurationError(f"technologies.{name}.{key} must be in (0, 1]")

    outage = model.get("outage")
    if outage is not None:
        if not isinstance(outage, dict):
            raise ConfigurationError("model.outage must be null or a mapping")
        if outage.get("technology") not in {"nuclear", "gas", "imports"}:
            raise ConfigurationError("Outage technology must be nuclear, gas, or imports")
        if int(outage.get("duration_hours", 0)) <= 0:
            raise ConfigurationError("Outage duration_hours must be positive")
        if not 0 <= float(outage.get("available_fraction", -1)) <= 1:
            raise ConfigurationError("Outage available_fraction must be between 0 and 1")


def discover_scenarios(directory: str | Path) -> list[Path]:
    """Return scenario files in stable order, excluding the shared base file."""

    paths = sorted(Path(directory).glob("*.yaml"))
    return [path for path in paths if path.name != "base.yaml"]

