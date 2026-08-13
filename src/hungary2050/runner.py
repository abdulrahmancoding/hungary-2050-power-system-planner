"""High-level orchestration for scenario runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hungary2050.config import discover_scenarios, load_scenario
from hungary2050.data import load_profiles
from hungary2050.model import build_network, optimize_network
from hungary2050.results import (
    build_comparison_table,
    calculate_results,
    create_comparison_charts,
    export_results,
)


class OptimizationError(RuntimeError):
    """Raised when HiGHS does not return an optimal solution."""


def run_scenario(
    scenario_path: str | Path,
    project_root: str | Path,
    hours: int | None = None,
) -> dict[str, Any]:
    """Load, build, optimize, calculate, and export one scenario."""

    root = Path(project_root)
    scenario = load_scenario(scenario_path, root / "scenarios" / "base.yaml")
    profiles = load_profiles(root / scenario.settings["data"]["path"], hours=hours)
    network = build_network(profiles, scenario)
    condition, termination = optimize_network(network)
    if condition.lower() != "ok" or termination.lower() != "optimal":
        raise OptimizationError(
            f"Scenario {scenario.slug} failed: condition={condition}, termination={termination}"
        )
    metrics = calculate_results(network, scenario, condition, termination)
    export_results(network, metrics, root / "results" / "tables")
    return metrics


def run_all(project_root: str | Path, hours: int | None = None) -> list[dict[str, Any]]:
    """Run every configured scenario and generate aggregate tables and figures."""

    root = Path(project_root)
    summaries = [
        run_scenario(path, root, hours=hours)
        for path in discover_scenarios(root / "scenarios")
    ]
    comparison = build_comparison_table(summaries)
    comparison.to_csv(root / "results" / "tables" / "scenario_comparison.csv", index=False, lineterminator="\n")
    create_comparison_charts(comparison, summaries, root / "results" / "figures")
    return summaries

