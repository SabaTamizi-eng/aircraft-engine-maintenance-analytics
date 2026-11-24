# Power BI

The report runs on either the Snowflake views or the local CSVs from
`python -m pipeline.export_powerbi_extract` (same table and column names), controlled by
the `SourceMode` parameter.

- `power_query/parameters.pq`: `SourceMode`, `DataFolder`, `SnowflakeServer`
- `power_query/fnLoadTable.pq`: loads one table from CSV or Snowflake
- `power_query/queries.pq`: the seven tables (Sensor Readings is unpivoted for CSV)
- `measures.dax`
- `theme.json`

## Model

- Fleet → Engine on `FLEET_ID`
- Engine → Engine Cycles, Engine Health (1:1), Sensor Readings on `ENGINE_KEY`
- Sensor → Sensor Readings on `SENSOR_ID`

`FLEET_ID` on the fact tables is only there for the Snowflake row access policy, so it's
hidden and fleets are filtered through the Fleet table. Auto date/time is off (the data is
in cycles, not dates).

## Pages

1. **Fleet overview**: engines in service, critical/warning counts, average RUL, health
   status by fleet, and a table of the engines closest to failure.
2. **Engine detail** (drill-through on `ENGINE_KEY`): sensor trends with a sensor slicer,
   actual RUL over cycles, current status.
3. **Reliability**: cycles to failure by fleet and sensor drift vs. early life.
4. **Model**: predicted vs. actual RUL, RMSE, MAE, share within 20 cycles, late predictions.
5. **Data quality**: check results and pass rate.

## Row-level security

Role `Fleets 1 and 3` with `[FLEET_ID] IN { "FD001", "FD003" }` on Fleet. In Snowflake the
same thing is done by the row access policy when connecting as `ENGINE_FLEET_VIEWER`.

Save as `.pbip` in this folder so the report and model are stored as text.
