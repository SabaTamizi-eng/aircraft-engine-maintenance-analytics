# Power BI report

The report reads the Snowflake reporting views. It can also run on local CSV files with the
same table and column names, so it can be built and reviewed without a Snowflake account.

| File | Purpose |
|---|---|
| `power_query/01_parameters.pq` | `SourceMode`, `DataFolder`, `SnowflakeServer` parameters |
| `power_query/02_fnLoadTable.pq` | One function that loads any table from CSV or Snowflake |
| `power_query/03_tables.pq` | The seven report tables, including the sensor unpivot |
| `measures.dax` | All DAX measures |
| `theme.json` | Report colour theme (View > Themes > Browse for themes) |

## Data model

See [docs/data_model.md](../docs/data_model.md) for the Snowflake star schema.

| From (one) | To (many) | Key |
|---|---|---|
| Fleet | Engine | `FLEET_ID` |
| Engine | Engine Cycles | `ENGINE_KEY` |
| Engine | Engine Health | `ENGINE_KEY` (one to one, single direction) |
| Engine | Sensor Readings | `ENGINE_KEY` |
| Sensor | Sensor Readings | `SENSOR_ID` |

Hide `FLEET_ID` on Engine Cycles, Engine Health and Sensor Readings (it exists for Snowflake
row-level security; filter fleets through the Fleet table). Turn off auto date/time, since
the data is measured in operating cycles, not dates.

## Report pages

1. **Fleet Overview**: cards for Engines In Service, Critical Engines, Warning Engines and
   Avg Remaining Useful Life; a stacked bar of in-service engines by fleet and health status;
   a table of the engines closest to failure (engine, fleet, current cycle, actual RUL,
   predicted RUL, health status) using `Health Status Color` for conditional formatting.
2. **Engine Detail** (drill-through on `ENGINE_KEY`): selected engine serial number, sensor
   readings over cycles with a sensor slicer, actual RUL over cycles, current health card.
3. **Fleet Reliability**: Avg Cycles to Failure and Shortest Life by fleet, distribution of
   cycles to failure, and Sensor Change vs Early Life % for the sensors used in the model.
4. **Model Performance**: predicted vs actual RUL scatter, RUL RMSE, RUL MAE,
   % Predictions Within 20 Cycles, and Late Predictions by health status.
5. **Data Quality**: the checks table with PASS/FAIL formatting, DQ Pass Rate and Last Data Check.

## Row-level security

- **In Power BI:** Modeling > Manage roles > new role `Fleets 1 and 3` with the filter
  `[FLEET_ID] IN { "FD001", "FD003" }` on the Fleet table. Test with View as.
- **In Snowflake:** connect with the `ENGINE_FLEET_VIEWER` role and the row access policy
  (`sql/05_governance.sql`) returns only fleets FD001 and FD003, with masked serial numbers.

## Build steps

1. Run the local pipeline from the repository root:
   `python -m pipeline.download_data`, `python -m pipeline.transform`,
   `python -m ml.train_rul_model`, `python -m pipeline.export_powerbi_extract`.
2. In Power BI Desktop, create the three parameters, then `fnLoadTable`, then the seven tables.
3. Create the relationships and measures above, apply `theme.json`, and build the pages.
4. Save as a **Power BI Project** (File > Save as > `.pbip`) into this folder, so the report
   and model are stored as text files that can be reviewed in Git.
5. To use Snowflake instead of CSV, set `SourceMode` to `Snowflake` and `SnowflakeServer` to
   your account URL, then refresh.
