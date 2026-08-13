# Sources and Data Provenance

Accessed: **2026-08-13**. Direct primary or official sources are preferred.
No external dataset is downloaded by the default workflow; the committed input
CSV is 387 KB and is created locally from deterministic code.

## Inputs used directly

### IPCC natural-gas emission factor

- Source: [2006 IPCC Guidelines for National Greenhouse Gas Inventories, Volume 2, Chapter 2: Stationary Combustion](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf)
- Authority: Intergovernmental Panel on Climate Change, Task Force on National
  Greenhouse Gas Inventories.
- Field: Table 2.2 default CO2 emission factor for natural gas in energy
  industries: 56,100 kg CO2/TJ on a net-calorific-value basis.
- Transformation: `56,100 kg/TJ × 0.0036 TJ/MWh = 201.96 kg/MWh`, stored as
  `0.202 tCO2/MWh_thermal`. Electrical emissions divide output by the assumed
  generator efficiency before applying this factor.
- Classification: official methodological default, then derived unit conversion.
- License/use: IPCC material; see [IPCC copyright and usage terms](https://www.ipcc.ch/copyright/).
- Limitation: a Tier 1 default, not plant-specific fuel composition or measured
  Hungarian emissions; upstream methane and lifecycle emissions are excluded.

## Official context and future calibration sources

These sources inform the project structure, field definitions, and limitations.
No numeric observations from them are silently embedded in the synthetic CSV.

### European Commission Joint Research Centre — PVGIS

- [PVGIS 5 API non-interactive service](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en)
- [Hourly radiation and PV output field definitions](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-tools/hourly-radiation_en)
- Relevant fields: UTC timestamp, PV power `P` (W), irradiance, temperature, and
  10 m wind speed. PV output can be normalized by nominal peak power to create
  a solar capacity factor.
- License/use: free and open access; [PVGIS usage conditions](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/usage-conditions_en).
- Limitation here: the project does not call the API, select a representative
  Hungarian location, or transform PVGIS observations. Solar data is synthetic.

### ENTSO-E Transparency Platform

- [Transparency Platform](https://transparency.entsoe.eu/)
- Relevant fields for a future data-backed version: Actual Total Load (MW),
  Actual Generation per Production Type (MW), and cross-border physical flows.
- [Terms and conditions](https://transparency.entsoe.eu/content/static_content/download?path=%2FStatic+content%2Fterms+and+conditions%2F230309_ENTSOE_Transparency_Terms_Conditions_MC_APPROVED.pdf)
  and [data available for reuse](https://transparency.entsoe.eu/content/static_content/Static%20content/terms%20and%20conditions/220218_List_of_Data_available_for_reuse.pdf).
- License/use: reuse status depends on dataset and primary data owner; the reuse
  list identifies items available under CC BY 4.0.
- Limitation here: no API token is required or included and no ENTSO-E data is
  committed. Time-zone, missing-value, and production-type mappings would need
  explicit treatment before use.

### Eurostat energy statistics

- [Energy data coverage and definitions](https://ec.europa.eu/eurostat/web/energy/information-data)
- [Energy statistics methodology](https://ec.europa.eu/eurostat/web/energy/methodology)
- [Eurostat web services](https://ec.europa.eu/eurostat/data/web-services)
- Relevant fields: annual/monthly electricity supply, transformation,
  consumption, generation by source, imports, and exports in MWh/GWh/TWh.
- License/use: [Eurostat copyright and free reuse policy](https://ec.europa.eu/eurostat/about-us/policies/copyright).
- Limitation here: used as a documented validation route, not as a numeric input.

### European Commission policy context

- [Commission Recommendation (EU) 2024/615 on Hungary's draft updated National Energy and Climate Plan](https://eur-lex.europa.eu/eli/reco/2024/615/oj/eng/pdf)
- Relevant use: official policy context for scenario design and an example of
  why planning assumptions must not be presented as adopted targets.
- License/use: EU legal documents are reusable under the Commission reuse policy.
- Limitation here: the 1 Mt model cap and technology limits are not values taken
  from this recommendation.

### Danish Energy Agency technology catalogues

- [Technology catalogues](https://ens.dk/technologydata)
- [Tools and publications](https://ens.dk/en/global-cooperation/tools-and-publications)
- Relevant fields for future calibration: investment cost, fixed and variable
  O&M, lifetime, efficiency, and technical characteristics by technology/year.
- License/use: see terms attached to each downloadable catalogue.
- Limitation here: current round-number cost assumptions were not extracted from
  individual catalogue rows. The source is recorded as a primary calibration
  path, not cited as support for the present numbers.

## Software and mathematical formulation

### PyPSA

- [PyPSA optimization overview](https://docs.pypsa.org/latest/user-guide/optimization/overview/)
- [Single-node capacity-expansion example and equations](https://docs.pypsa.org/latest/examples/capacity-expansion-planning-single-node/)
- [Global constraints](https://docs.pypsa.org/latest/user-guide/optimization/global-constraints/)
- [Storage constraints](https://docs.pypsa.org/latest/user-guide/optimization/storage/)
- Version used: 1.2.4, installed from PyPI.
- License: MIT; see the upstream distribution metadata/repository.

### HiGHS

- [HiGHS official site and documentation](https://highs.dev/)
- Version used: `highspy` 1.15.1. HiGHS solves the continuous linear program.
- License: MIT.

## Synthetic processed dataset

File: `data/processed/hourly_profiles.csv`

| Field | Unit | Definition | Transformation |
|---|---|---|---|
| `timestamp` | naive hourly datetime | 8,760 consecutive labels for non-leap 2021 | `pandas.date_range`, hourly, left-inclusive |
| `demand_mw` | MW | synthetic national-node load | normalized deterministic seasonal + daily + weekly + texture formula; annual mean 7,500 MW |
| `solar_capacity_factor` | per unit | maximum available solar output per MW | deterministic daylight envelope × seasonal irradiance × cloud modulation, clipped [0,1] |
| `wind_capacity_factor` | per unit | maximum available wind output per MW | deterministic seasonal and multi-frequency terms, clipped [0.03,0.78] |

The generator is `src/hungary2050/data.py`. Values are rounded to 3 decimals
for demand and 6 decimals for capacity factors. Regeneration is deterministic;
tests enforce valid ranges, consecutive timestamps, and mean demand.

### Dataset license and limitations

The synthetic CSV and generation code are released under the repository MIT
license. They contain no copied third-party observations. The series preserves
plausible qualitative structure but not measured correlations, extremes,
forecast uncertainty, geography, or climate-change effects. It is suitable for
testing model mechanics, not for investment or policy decisions.

