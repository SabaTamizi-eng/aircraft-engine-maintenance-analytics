// one blank query each, named as below (measures.dax uses these names)

// ---- Fleet ----
let Source = fnLoadTable("DIM_FLEET") in Source

// ---- Engine ----
let Source = fnLoadTable("DIM_ENGINE") in Source

// ---- Sensor ----
let Source = fnLoadTable("DIM_SENSOR") in Source

// ---- Engine Cycles ----
let Source = fnLoadTable("VW_ENGINE_CYCLE_RUL") in Source

// ---- Engine Health ----
let Source = fnLoadTable("VW_ENGINE_CURRENT_HEALTH") in Source

// ---- Data Quality ----
let Source = fnLoadTable("VW_DATA_QUALITY_CHECKS") in Source

// ---- Sensor Readings ----
// Snowflake has a view for this; with CSV the sensor columns are unpivoted here
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
