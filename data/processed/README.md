# Processed data

`hourly_profiles.csv` is a deterministic, synthetic 8,760-hour demonstration
year produced by `src/hungary2050/data.py`. It is committed because it is small,
human-inspectable, and lets model runs start immediately. Regenerate it with:

```powershell
.\.venv\Scripts\python.exe -m hungary2050 prepare-data
```

The CSV is not an official Hungarian load or weather record. See `SOURCES.md`
and `ASSUMPTIONS.md` for provenance and limitations.

