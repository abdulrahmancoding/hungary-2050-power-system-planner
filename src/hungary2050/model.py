"""PyPSA one-node capacity-expansion model construction and optimization."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pypsa

from hungary2050.config import Scenario


def _generator_kwargs(technology: dict[str, Any]) -> dict[str, Any]:
    existing = float(technology["existing_capacity_mw"])
    maximum = float(technology["max_capacity_mw"])
    extendable = bool(technology.get("extendable", False))
    return {
        "p_nom": existing,
        "p_nom_extendable": extendable,
        "p_nom_min": existing if extendable else 0.0,
        "p_nom_max": maximum if extendable else np.inf,
        "capital_cost": float(technology.get("capital_cost_eur_per_mw_year", 0.0)),
        "marginal_cost": float(technology.get("marginal_cost_eur_per_mwh", 0.0)),
        "efficiency": float(technology.get("efficiency", 1.0)),
    }


def build_network(profiles: pd.DataFrame, scenario: Scenario) -> pypsa.Network:
    """Build a one-bus Hungary model from validated profiles and scenario settings."""

    cfg = scenario.settings
    model_cfg = cfg["model"]
    technologies = cfg["technologies"]

    network = pypsa.Network()
    network.name = f"Hungary 2050 — {scenario.name}"
    network.meta = {
        "scenario_slug": scenario.slug,
        "description": scenario.description,
        "data_classification": "synthetic demonstration data and modelling assumptions",
    }
    network.set_snapshots(profiles.index)
    network.snapshot_weightings.loc[:, ["objective", "generators", "stores"]] = 1.0
    network.add("Carrier", "AC")
    network.add("Bus", "hungary", carrier="AC")

    emission_factors = {
        "gas": float(technologies["gas"].get("co2_emissions_t_per_mwh_thermal", 0.0)),
        "imports": float(technologies["imports"].get("co2_emissions_t_per_mwh", 0.0)),
    }
    for carrier in ("solar", "wind", "nuclear", "gas", "imports", "battery", "load_shedding"):
        network.add("Carrier", carrier, co2_emissions=emission_factors.get(carrier, 0.0))

    demand = profiles["demand_mw"] * float(model_cfg["demand_multiplier"])
    network.add("Load", "electricity_demand", bus="hungary", p_set=demand)

    availability = {
        "solar": profiles["solar_capacity_factor"]
        * float(model_cfg["solar_availability_multiplier"]),
        "wind": profiles["wind_capacity_factor"]
        * float(model_cfg["wind_availability_multiplier"]),
        "nuclear": pd.Series(
            float(technologies["nuclear"].get("availability", 1.0)), index=profiles.index
        ),
        "gas": pd.Series(float(technologies["gas"].get("availability", 1.0)), index=profiles.index),
        "imports": pd.Series(1.0, index=profiles.index),
    }

    outage = model_cfg.get("outage")
    if outage:
        technology = str(outage["technology"])
        start = pd.Timestamp(str(outage["start"])).tz_localize(None)
        end = start + pd.Timedelta(hours=int(outage["duration_hours"]))
        mask = (availability[technology].index >= start) & (availability[technology].index < end)
        if not mask.any():
            raise ValueError(f"Outage window does not overlap model snapshots: {outage}")
        availability[technology].loc[mask] *= float(outage["available_fraction"])

    for technology in ("solar", "wind", "nuclear", "gas", "imports"):
        network.add(
            "Generator",
            technology,
            bus="hungary",
            carrier=technology,
            p_max_pu=availability[technology],
            **_generator_kwargs(technologies[technology]),
        )

    battery = technologies["battery"]
    existing_battery = float(battery["existing_capacity_mw"])
    network.add(
        "StorageUnit",
        "battery",
        bus="hungary",
        carrier="battery",
        p_nom=existing_battery,
        p_nom_extendable=bool(battery.get("extendable", True)),
        p_nom_min=existing_battery,
        p_nom_max=float(battery["max_capacity_mw"]),
        max_hours=float(battery["duration_hours"]),
        efficiency_store=float(battery["efficiency_store"]),
        efficiency_dispatch=float(battery["efficiency_dispatch"]),
        standing_loss=float(battery.get("standing_loss_per_hour", 0.0)),
        cyclic_state_of_charge=True,
        capital_cost=float(battery["capital_cost_eur_per_mw_year"]),
        marginal_cost=float(battery.get("marginal_cost_eur_per_mwh", 0.0)),
    )

    shedding = technologies["load_shedding"]
    network.add(
        "Generator",
        "load_shedding",
        bus="hungary",
        carrier="load_shedding",
        p_nom=float(shedding["existing_capacity_mw"]),
        marginal_cost=float(shedding["marginal_cost_eur_per_mwh"]),
    )

    co2_cap = model_cfg.get("co2_cap_tonnes")
    if co2_cap is not None:
        network.add(
            "GlobalConstraint",
            "annual_co2_limit",
            type="primary_energy",
            carrier_attribute="co2_emissions",
            sense="<=",
            constant=float(co2_cap),
        )
    return network


def optimize_network(network: pypsa.Network) -> tuple[str, str]:
    """Solve the linear model with HiGHS and return condition and termination status."""

    condition, termination = network.optimize(
        solver_name="highs",
        include_objective_constant=False,
        solver_options={"output_flag": False, "log_to_console": False},
    )
    return str(condition), str(termination)
