"""Fast construction and optimization tests."""

import pandas as pd
import pypsa

from hungary2050.model import build_network, optimize_network


def test_network_contains_required_components(short_profiles, baseline_scenario) -> None:
    network = build_network(short_profiles, baseline_scenario)
    assert isinstance(network, pypsa.Network)
    assert list(network.buses.index) == ["hungary"]
    assert {"solar", "wind", "nuclear", "gas", "imports", "load_shedding"}.issubset(
        network.generators.index
    )
    assert "battery" in network.storage_units.index
    assert len(network.snapshots) == 48


def test_small_model_optimizes(short_profiles, baseline_scenario) -> None:
    network = build_network(short_profiles, baseline_scenario)
    condition, termination = optimize_network(network)
    assert condition == "ok"
    assert termination == "optimal"
    assert pd.notna(network.objective)

