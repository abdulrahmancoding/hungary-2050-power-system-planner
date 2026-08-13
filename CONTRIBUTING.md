# Contributing

Contributions that improve validation, transparent provenance, scenarios, or
documentation are welcome.

## Local checks

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m hungary2050 prepare-data
.\.venv\Scripts\python.exe -m pytest -q
```

Run all annual scenarios only when changes affect modelling or results:

```powershell
.\.venv\Scripts\python.exe -m hungary2050 run-all
```

## Data and modelling rules

- Classify each input as official, derived, or a modelling assumption.
- Add direct links, access date, field definitions, transformations, licenses,
  and limitations to `SOURCES.md` for new data.
- Never commit credentials, API tokens, virtual environments, solver logs, or
  unnecessarily large raw extracts.
- Ask before adding any dataset larger than 200 MB.
- Update tests and regenerate committed outputs when assumptions change.
- Do not present synthetic scenarios as forecasts or official policy.

