# Data schemas

Bundled JSON Schemas:

- `assets/schemas/source_record.schema.json`
- `assets/schemas/forecast_case.schema.json`
- `assets/schemas/forecast_snapshot.schema.json`
- `assets/schemas/backtest_result.schema.json`

Use stable IDs. Dates must be explicit. Every forecast case must include `as_of`, archetypes, horizons, evidence references, actual values only in the validation section, and separate fact/assumption labels.
