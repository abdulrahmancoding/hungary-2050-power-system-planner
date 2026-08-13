# Assumptions Register

This register separates source-derived values from modelling assumptions. Unless
a row says **official** or **derived**, values are exploratory assumptions for a
transparent demonstration model. They are not Hungarian statistics or forecasts.

## Data classification

| Item | Value or method | Classification | Rationale / limitation |
|---|---|---|---|
| Time horizon | 8,760 hourly snapshots labelled 2021 | Modelling assumption | A non-leap label enables a compact chronological demonstration year; it is not 2021 observed data. |
| Demand | 7,500 MW annual mean with deterministic seasonal, daily, weekly, and 9-day terms | Synthetic modelling assumption | Formula is in `src/hungary2050/data.py`; mean implies 65.7 TWh before scenario scaling. |
| Solar availability | Deterministic daylight/season/cloud formula, bounded [0,1] | Synthetic modelling assumption informed by PVGIS field concepts | Not downloaded from PVGIS and not calibrated to a Hungarian site. |
| Wind availability | Deterministic seasonal and multi-frequency formula, bounded [0.03,0.78] | Synthetic modelling assumption | Not reanalysis, measured production, or a turbine power-curve calculation. |
| Natural-gas CO2 factor | 0.202 tCO2/MWh thermal | Derived from an official methodology | 56.1 tCO2/TJ × 3.6 GJ/MWh = 0.20196 tCO2/MWh, rounded to 0.202; IPCC 2006 Guidelines Volume 2, Table 2.2. |
| Import CO2 factor | 0.180 tCO2/MWh electricity | Modelling assumption | Constant proxy; real marginal import intensity varies by hour, border, and market conditions. |

## Shared technology assumptions

All capacities and costs below are scenario inputs, not a statement of current
or planned Hungarian assets. `capital_cost` is an annualized power-capacity cost
in EUR/MW-year. Fixed existing assets use zero capital cost in the objective;
extendable assets pay the listed cost on their full optimized capacity, including
the specified minimum existing capacity.

| Technology | Existing (MW) | Maximum (MW) | Annual capital cost (EUR/MW-y) | Marginal cost (EUR/MWh) | Other assumptions |
|---|---:|---:|---:|---:|---|
| Solar | 4,000 | 14,000 | 55,000 | 0 | Extendable; hourly synthetic availability |
| Wind | 500 | 10,000 | 95,000 | 0 | Extendable; hourly synthetic availability |
| Nuclear | 2,400 | 2,400 | 0 | 12 | Fixed; 90% availability; no minimum stable output |
| Natural gas | 4,500 | 8,000 | 45,000 | 95 | Extendable; 55% efficiency; 95% availability |
| Battery | 100 | 6,000 | 110,000 | 1 on discharge | Extendable; 4 h; 95% charge and discharge efficiency; 0.01% hourly standing loss; cyclic |
| Imports | 3,500 | 3,500 | 0 | 90 | Fixed firm limit; unlimited annual energy within hourly capacity |
| Load shedding | 20,000 | 20,000 | 0 | 10,000 | Feasibility device and unserved-energy measure |

The cost assumptions are deliberately round values selected for scenario
behavior. The Danish Energy Agency technology catalogues are listed in
`SOURCES.md` as an appropriate primary source for future calibration, but the
present values were not extracted from specific catalogue rows and must not be
represented as source-derived.

## Scenario-specific assumptions

| Scenario | Override | Classification |
|---|---|---|
| Low-carbon 2050 | Operational CO2 <= 1,000,000 t/year; solar max 18 GW; wind max 14 GW; battery max 8 GW | Modelling assumption; cap chosen to bind in this demonstration, not an official target |
| High electricity demand | Every hourly demand value × 1.30 | Modelling assumption representing strong electrification |
| Low renewables | Every solar and wind capacity factor × 0.65 | Climate-stress modelling assumption; not a climate projection |
| Major outage | Nuclear availability multiplied by 0.25 for 336 h from 2021-01-11 | Reliability-stress modelling assumption |
| Limited imports | Import power capacity 1,000 MW | Energy-security modelling assumption |

## Accounting conventions

- One-hour snapshot weights mean MW summed over snapshots produces MWh.
- Gas emissions use electrical dispatch divided by efficiency, then multiplied
  by the thermal fuel emission factor. Import emissions multiply imported MWh
  by the assumed direct intensity.
- Emissions cover modeled operations only; construction, fuel supply chains,
  methane leakage, and decommissioning are excluded.
- Renewable curtailment equals potential energy at optimized capacity minus
  dispatched renewable energy; numerical negatives are clipped to zero.
- Battery power capacity and energy capacity are linked by the fixed four-hour
  duration, so energy and power are not independently optimized.
- The solver has perfect information about the entire demonstration year.
- Monetary values are nominal EUR-like input values with no base year, inflation,
  or exchange-rate conversion. Results are internally comparable only.

