"""Result calculation, tabular export, and cross-scenario visualization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
import pypsa

from hungary2050.config import Scenario

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


GENERATION_ORDER = ["solar", "wind", "nuclear", "gas", "imports", "load_shedding"]
COLORS = {
    "solar": "#F5C542",
    "wind": "#4DA3D9",
    "nuclear": "#8E6BBE",
    "gas": "#8B8B8B",
    "imports": "#4C956C",
    "load_shedding": "#D1495B",
    "battery": "#E07A5F",
}


def _capacity(network: pypsa.Network, component: str, attribute: str, name: str) -> float:
    table = getattr(network, component)
    optimized = f"{attribute}_opt"
    if optimized in table.columns:
        return float(table.at[name, optimized])
    return float(table.at[name, attribute])


def calculate_results(
    network: pypsa.Network,
    scenario: Scenario,
    condition: str,
    termination: str,
) -> dict[str, Any]:
    """Calculate cost, emissions, capacity, energy, storage, curtailment, and reliability metrics."""

    weights = network.snapshot_weightings.generators
    generator_dispatch = network.generators_t.p.mul(weights, axis=0)
    generation_mwh = {
        name: float(generator_dispatch[name].sum()) for name in GENERATION_ORDER
    }

    capacities = {
        name: _capacity(network, "generators", "p_nom", name)
        for name in GENERATION_ORDER
        if name != "load_shedding"
    }
    capacities["battery"] = _capacity(network, "storage_units", "p_nom", "battery")

    battery_power = network.storage_units_t.p["battery"]
    store_weights = network.snapshot_weightings.stores
    battery_discharge = float(battery_power.clip(lower=0).mul(store_weights).sum())
    battery_charge = float((-battery_power.clip(upper=0)).mul(store_weights).sum())

    emissions = 0.0
    for name in ("gas", "imports"):
        carrier = network.generators.at[name, "carrier"]
        factor = float(network.carriers.at[carrier, "co2_emissions"])
        efficiency = float(network.generators.at[name, "efficiency"])
        emissions += generation_mwh[name] * factor / efficiency

    renewable_curtailment: dict[str, float] = {}
    for name in ("solar", "wind"):
        available = (
            network.generators_t.p_max_pu[name]
            * capacities[name]
            * network.snapshot_weightings.generators
        ).sum()
        renewable_curtailment[name] = float(max(0.0, available - generation_mwh[name]))

    # Reconstruct objective components to keep the accounting transparent.
    capital_cost = 0.0
    for name, row in network.generators.iterrows():
        if bool(row.p_nom_extendable):
            capital_cost += float(row.p_nom_opt) * float(row.capital_cost)
    battery_row = network.storage_units.loc["battery"]
    if bool(battery_row.p_nom_extendable):
        capital_cost += float(battery_row.p_nom_opt) * float(battery_row.capital_cost)
    operating_cost = sum(
        generation_mwh[name] * float(network.generators.at[name, "marginal_cost"])
        for name in GENERATION_ORDER
    )
    operating_cost += battery_discharge * float(battery_row.marginal_cost)

    objective = float(network.objective)
    balance_gap = objective - capital_cost - operating_cost
    return {
        "scenario": scenario.name,
        "slug": scenario.slug,
        "description": scenario.description,
        "optimization_status": condition,
        "termination_condition": termination,
        "total_annualized_system_cost_eur": objective,
        "annualized_capital_cost_eur": capital_cost,
        "operating_cost_eur": operating_cost,
        "cost_reconciliation_difference_eur": balance_gap,
        "co2_emissions_tonnes": emissions,
        "installed_capacity_mw": capacities,
        "generation_mwh": generation_mwh,
        "battery_charging_mwh": battery_charge,
        "battery_discharging_mwh": battery_discharge,
        "imports_mwh": generation_mwh["imports"],
        "renewable_curtailment_mwh": renewable_curtailment,
        "unserved_energy_mwh": generation_mwh["load_shedding"],
    }


def _flatten_results(metrics: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, value in metrics.items():
        if isinstance(value, dict):
            for item, item_value in value.items():
                rows.append({"metric": key, "technology": item, "value": item_value})
        elif isinstance(value, (str, int, float, np.number)):
            rows.append({"metric": key, "technology": "", "value": value})
    return pd.DataFrame(rows)


def export_results(
    network: pypsa.Network,
    metrics: dict[str, Any],
    output_directory: str | Path,
) -> Path:
    """Export one scenario's metrics, capacity, energy, and hourly dispatch tables."""

    output = Path(output_directory) / str(metrics["slug"])
    output.mkdir(parents=True, exist_ok=True)
    with (output / "summary.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(metrics, handle, indent=2, sort_keys=True)
        handle.write("\n")
    _flatten_results(metrics).to_csv(output / "summary.csv", index=False, lineterminator="\n")

    pd.Series(metrics["installed_capacity_mw"], name="capacity_mw").rename_axis("technology").to_csv(
        output / "capacity.csv", lineterminator="\n"
    )
    pd.Series(metrics["generation_mwh"], name="generation_mwh").rename_axis("technology").to_csv(
        output / "generation.csv", lineterminator="\n"
    )

    dispatch = network.generators_t.p.copy()
    dispatch["battery_discharge_mw"] = network.storage_units_t.p["battery"].clip(lower=0)
    dispatch["battery_charge_mw"] = -network.storage_units_t.p["battery"].clip(upper=0)
    dispatch["battery_state_of_charge_mwh"] = network.storage_units_t.state_of_charge["battery"]
    dispatch.index.name = "timestamp"
    dispatch.to_csv(output / "hourly_dispatch.csv", lineterminator="\n")
    return output


def load_exported_summaries(results_directory: str | Path) -> list[dict[str, Any]]:
    """Load all scenario JSON summaries from a results directory."""

    summaries = []
    for path in sorted(Path(results_directory).glob("*/summary.json")):
        summaries.append(json.loads(path.read_text(encoding="utf-8")))
    return summaries


def build_comparison_table(summaries: list[dict[str, Any]]) -> pd.DataFrame:
    """Create one row per scenario with the principal comparison metrics."""

    rows = []
    for item in summaries:
        row = {
            "scenario": item["scenario"],
            "slug": item["slug"],
            "status": item["optimization_status"],
            "termination": item["termination_condition"],
            "system_cost_billion_eur": item["total_annualized_system_cost_eur"] / 1e9,
            "co2_emissions_mt": item["co2_emissions_tonnes"] / 1e6,
            "imports_twh": item["imports_mwh"] / 1e6,
            "curtailment_twh": sum(item["renewable_curtailment_mwh"].values()) / 1e6,
            "unserved_energy_gwh": item["unserved_energy_mwh"] / 1e3,
            "battery_charge_twh": item["battery_charging_mwh"] / 1e6,
            "battery_discharge_twh": item["battery_discharging_mwh"] / 1e6,
        }
        row.update({f"capacity_{key}_gw": value / 1e3 for key, value in item["installed_capacity_mw"].items()})
        row.update({f"generation_{key}_twh": value / 1e6 for key, value in item["generation_mwh"].items()})
        rows.append(row)
    return pd.DataFrame(rows)


def create_comparison_charts(
    comparison: pd.DataFrame,
    summaries: list[dict[str, Any]],
    figures_directory: str | Path,
) -> list[Path]:
    """Render professional static charts comparing cost, emissions, capacity, and energy."""

    figures = Path(figures_directory)
    figures.mkdir(parents=True, exist_ok=True)
    labels = comparison["scenario"].tolist()
    x = np.arange(len(labels))
    paths: list[Path] = []

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), constrained_layout=True)
    axes[0].bar(x, comparison["system_cost_billion_eur"], color="#2F6690")
    axes[0].set_ylabel("Annual system cost (billion EUR)")
    axes[0].set_title("Optimized annualized system cost")
    axes[1].bar(x, comparison["co2_emissions_mt"], color="#6A994E")
    axes[1].set_ylabel("Operational CO2 (Mt)")
    axes[1].set_title("Modelled operational emissions")
    for axis in axes:
        axis.set_xticks(x, labels, rotation=25, ha="right")
    fig.suptitle("Hungary 2050 scenario comparison — synthetic demonstration study", fontsize=14)
    path = figures / "cost_and_emissions.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path)

    capacity = pd.DataFrame(
        {item["scenario"]: item["installed_capacity_mw"] for item in summaries}
    ).T.div(1000)
    capacity = capacity.reindex(columns=["solar", "wind", "nuclear", "gas", "battery", "imports"])
    fig, axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
    capacity.plot(kind="bar", stacked=True, ax=axis, color=[COLORS.get(c, "#777777") for c in capacity.columns])
    axis.set_ylabel("Installed power capacity (GW)")
    axis.set_xlabel("")
    axis.set_title("Optimized capacity mix by scenario")
    axis.tick_params(axis="x", rotation=25)
    axis.legend(title="Technology", ncol=3)
    path = figures / "capacity_mix.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path)

    generation = pd.DataFrame({item["scenario"]: item["generation_mwh"] for item in summaries}).T.div(1e6)
    generation = generation.reindex(columns=GENERATION_ORDER)
    fig, axis = plt.subplots(figsize=(12, 6), constrained_layout=True)
    generation.plot(kind="bar", stacked=True, ax=axis, color=[COLORS[c] for c in generation.columns])
    axis.set_ylabel("Electricity supplied (TWh)")
    axis.set_xlabel("")
    axis.set_title("Annual electricity balance by scenario")
    axis.tick_params(axis="x", rotation=25)
    axis.legend(title="Source", ncol=3)
    path = figures / "generation_mix.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), constrained_layout=True)
    axes[0].bar(x, comparison["imports_twh"], color=COLORS["imports"])
    axes[0].set_ylabel("Imports (TWh)")
    axes[0].set_title("Annual imports")
    axes[1].bar(x, comparison["curtailment_twh"], color="#7CB342")
    axes[1].set_ylabel("Curtailment (TWh)")
    axes[1].set_title("Renewable curtailment")
    axes[2].bar(x, comparison["unserved_energy_gwh"] * 1000, color=COLORS["load_shedding"])
    axes[2].set_ylabel("Unserved energy (MWh)")
    axes[2].set_title("Reliability shortfall")
    for axis in axes:
        axis.set_xticks(x, labels, rotation=28, ha="right")
    fig.suptitle("Security and flexibility indicators — synthetic demonstration study", fontsize=14)
    path = figures / "security_and_flexibility.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(path)
    return paths
