// One query per table; the names match the tables in the model and measures.dax

// ---- Fleet ----
let
    Source = fnLoadTable("DIM_FLEET"),
    Selected = Table.SelectColumns(Source, {"FLEET_ID", "FLEET_NAME", "OPERATING_CONDITIONS", "OPERATING_CONDITION_DESC", "FAULT_MODES", "FAULT_MODE_COUNT"})
in
    Selected

// ---- Engine ----
let
    Source = fnLoadTable("DIM_ENGINE"),
    Selected = Table.SelectColumns(Source, {"ENGINE_KEY", "ENGINE_SERIAL_NUMBER", "FLEET_ID", "DATASET_SPLIT", "UNIT_NUMBER", "ENGINE_LIFECYCLE"})
in
    Selected

// ---- Sensor ----
let
    Source = fnLoadTable("DIM_SENSOR"),
    Selected = Table.SelectColumns(Source, {"SENSOR_ID", "SENSOR_SYMBOL", "SENSOR_DESCRIPTION", "UNIT_OF_MEASURE", "USED_IN_BASELINE_MODEL"})
in
    Selected

// ---- Engine Cycles ----
let
    Source = fnLoadTable("VW_ENGINE_CYCLE_RUL"),
    Selected = Table.SelectColumns(Source, {"ENGINE_KEY", "FLEET_ID", "CYCLE", "ACTUAL_RUL", "HEALTH_STATUS"})
in
    Selected

// ---- Engine Health ----
let
    Source = fnLoadTable("VW_ENGINE_CURRENT_HEALTH"),
    Selected = Table.SelectColumns(Source, {"ENGINE_KEY", "FLEET_ID", "DATASET_SPLIT", "ENGINE_LIFECYCLE", "CURRENT_CYCLE", "ACTUAL_RUL", "HEALTH_STATUS", "PREDICTED_RUL", "MODEL_NAME", "MODEL_VERSION", "ACTUAL_RUL_AT_PREDICTION", "PREDICTION_ERROR"}),
    WithSort = Table.AddColumn(Selected, "HEALTH_SORT", each if [HEALTH_STATUS] = "Critical" then 1 else if [HEALTH_STATUS] = "Warning" then 2 else 3, Int64.Type)
in
    WithSort

// ---- Sensor Readings ----
let
    Long =
        if SourceMode = "Snowflake" then
            Table.SelectColumns(fnLoadTable("VW_SENSOR_READINGS_LONG"), {"ENGINE_KEY", "FLEET_ID", "CYCLE", "SENSOR_ID", "READING"})
        else
            let
                KeyColumns = {"ENGINE_KEY", "FLEET_ID", "CYCLE"},
                SensorColumns = List.Transform({1..21}, each "SENSOR_" & Text.From(_)),
                Kept = Table.SelectColumns(fnLoadTable("VW_ENGINE_CYCLE_RUL"), KeyColumns & SensorColumns),
                Unpivoted = Table.UnpivotOtherColumns(Kept, KeyColumns, "SENSOR_COLUMN", "READING"),
                WithId = Table.AddColumn(Unpivoted, "SENSOR_ID", each Number.From(Text.AfterDelimiter([SENSOR_COLUMN], "_")), Int64.Type),
                Result = Table.SelectColumns(WithId, {"ENGINE_KEY", "FLEET_ID", "CYCLE", "SENSOR_ID", "READING"})
            in
                Result
in
    Long

// ---- Data Quality ----
let
    Source = fnLoadTable("VW_DATA_QUALITY_CHECKS"),
    Selected = Table.SelectColumns(Source, {"CHECK_NAME", "CATEGORY", "FAILING_ROWS", "STATUS", "CHECKED_AT"})
in
    Selected
