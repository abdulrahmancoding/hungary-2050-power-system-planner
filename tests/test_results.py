"""Tests for result accounting and reliability metrics."""

import pytest

from hungary2050.model import build_network, optimize_network
from hungary2050.results import build_comparison_table, calculate_results


def test_result_calculation_reconciles_objective(short_profiles, baseline_scenario) -> None:
    network = build_network(short_profiles, baseline_scenario)
    condition, termination = optimize_network(network)
    results = calculate_results(network, baseline_scenario, condition, termination)
    assert results["optimization_status"] == "ok"
    assert results["termination_condition"] == "optimal"
    assert results["total_annualized_system_cost_eur"] > 0
    assert results["co2_emissions_tonnes"] >= 0
    assert results["unserved_energy_mwh"] >= 0
    assert abs(results["cost_reconciliation_difference_eur"]) < 0.01
    assert results["battery_charging_mwh"] >= 0
    assert results["battery_discharging_mwh"] >= 0

    comparison = build_comparison_table([results])
    assert comparison.loc[0, "scenario"] == "Baseline"
    assert comparison.loc[0, "system_cost_billion_eur"] > 0


def test_low_carbon_constraint_is_respected(short_profiles, baseline_scenario) -> None:
    # A short-horizon smoke check with a cap far above these 48-hour emissions.
    baseline_scenario.settings["model"]["co2_cap_tonnes"] = 1_000_000
    network = build_network(short_profiles, baseline_scenario)
    condition, termination = optimize_network(network)
    results = calculate_results(network, baseline_scenario, condition, termination)
    assert results["co2_emissions_tonnes"] <= 1_000_000 + 1e-6

