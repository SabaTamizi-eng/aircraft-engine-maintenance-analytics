// Create one Blank Query per table below. Use the query name shown, so the DAX
// measures in ../measures.dax work without changes.

// ---- Query name: Fleet ----
let Source = fnLoadTable("DIM_FLEET") in Source

// ---- Query name: Engine ----
let Source = fnLoadTable("DIM_ENGINE") in Source

// ---- Query name: Sensor ----
let Source = fnLoadTable("DIM_SENSOR") in Source

// ---- Query name: Engine Cycles ----
let Source = fnLoadTable("VW_ENGINE_CYCLE_RUL") in Source

// ---- Query name: Engine Health ----
let Source = fnLoadTable("VW_ENGINE_CURRENT_HEALTH") in Source

// ---- Query name: Data Quality ----
let Source = fnLoadTable("VW_DATA_QUALITY_CHECKS") in Source

// ---- Query name: Sensor Readings ----
// Long format (one row per engine, cycle and sensor) for trend charts.
// Snowflake already provides this as a view; for CSV it is built here by unpivoting.
let
    Long =
        if SourceMode = "Snowflake" then
            fnLoadTable("VW_SENSOR_READINGS_LONG")
        else
            let
                KeyColumns = {"ENGINE_KEY", "FLEET_ID", "CYCLE"},
                SensorColumns = List.Transform({1..21}, each "SENSOR_" & Text.From(_)),
                Kept = Table.SelectColumns(#"Engine Cycles", KeyColumns & SensorColumns),
                Unpivoted = Table.UnpivotOtherColumns(Kept, KeyColumns, "SENSOR_COLUMN", "READING"),
                WithId = Table.AddColumn(
                    Unpivoted, "SENSOR_ID",
                    each Number.From(Text.AfterDelimiter([SENSOR_COLUMN], "_")), Int64.Type
                ),
                Result = Table.RemoveColumns(WithId, {"SENSOR_COLUMN"})
            in
                Result
in
    Long
