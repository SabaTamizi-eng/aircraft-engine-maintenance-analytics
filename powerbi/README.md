# Power BI

`EngineMaintenance.pbip` is a Power BI Project: the semantic model is stored as TMDL
(`EngineMaintenance.SemanticModel/`) and the report as PBIR (`EngineMaintenance.Report/`),
so both can be reviewed in Git. `measures.dax` (all 56 measures) and `power_query/` (the M
code) are readable copies taken from the model.

![Fleet overview](../docs/images/fleet-overview.png)

## Opening it

1. Run the local pipeline from the repository root (`python -m pipeline.download_data`,
   `python -m pipeline.transform`, `python -m ml.train_rul_model`,
   `python -m pipeline.export_powerbi_extract`).
2. Open `EngineMaintenance.pbip` in Power BI Desktop.
3. Transform data > Edit parameters, set `DataFolder` to your `data\powerbi\` folder
   (with the trailing backslash), then Refresh.

To read from Snowflake instead, set `SourceMode` to `Snowflake` and `SnowflakeServer` to
your account URL. Table and column names are the same in both sources, and
`fnLoadTable` applies the same column types to both (Snowflake returns whole numbers as
decimals). Power BI signs in as a read-only service user: run
`sql/08_powerbi_reader.sql`, create a programmatic access token for `POWERBI_READER`,
and use it as the password with the **Snowflake** sign-in option.

## Model

| Table | Source | Notes |
|---|---|---|
| Fleet, Engine, Sensor | `DIM_*` | dimensions |
| Engine Cycles | `VW_ENGINE_CYCLE_RUL` | one row per engine and cycle |
| Engine Health | `VW_ENGINE_CURRENT_HEALTH` | latest cycle per engine, with predictions |
| Sensor Readings | `VW_SENSOR_READINGS_LONG` | unpivoted in Power Query when reading CSV |
| Data Quality | `VW_DATA_QUALITY_CHECKS` | |
| _Measures | | 56 DAX measures in display folders: fleet health, reliability, model, sensors, engine detail, data quality, labels, formatting |

All tables load through one Power Query function, `fnLoadTable`, which switches between
CSV and Snowflake. `FLEET_ID` on the fact tables is hidden; it's there for the Snowflake row
access policy.

## Pages

| Page | What it answers |
|---|---|
| Fleet overview | How many in-service engines are critical, and which ones need maintenance first (actual vs. predicted RUL) |
| Engine detail | How one engine's sensors drift as it wears out, and which sensors changed most between its first and last 20 cycles |
| Reliability | How long engines last per fleet, and which sensors change most |
| Model performance | How accurate the RUL predictions are, near failure and overall, and where the errors are |
| Data quality | Whether the data passed its checks and what was loaded per fleet |

"Near failure" means 125 cycles or fewer left, the range the model is trained to tell
apart (the training target is capped at 125).

## Design

- Page backgrounds (sidebar, tiles, KPI accents and icons) are images in
  `EngineMaintenance.Report/StaticResources/RegisteredResources/`; the visuals sit on top
  with transparent backgrounds.
- `theme.json` sets fonts, title styles and axis colours for every visual.
- The sidebar items are page navigation buttons (Ctrl + click in Desktop).
- On Engine detail the sensor dropdown is set not to filter the "which sensors changed
  most" chart (visual interactions), so that chart always shows every sensor.
- Table status colours come from the `Health Status Color` / `Health Status Font Color`
  measures (conditional formatting by field value).
