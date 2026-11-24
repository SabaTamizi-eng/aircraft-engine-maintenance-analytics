// fnLoadTable("VW_ENGINE_CURRENT_HEALTH") -> table from CSV or Snowflake, based on SourceMode
(tableName as text) as table =>
let
    FromCsv = () =>
        let
            Raw = Csv.Document(
                File.Contents(DataFolder & tableName & ".csv"),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
            Promoted = Table.PromoteHeaders(Raw, [PromoteAllScalars = true]),
            Columns = Table.ColumnNames(Promoted),

            TextColumns = {
                "ENGINE_KEY", "ENGINE_SERIAL_NUMBER", "FLEET_ID", "DATASET_SPLIT", "ENGINE_LIFECYCLE",
                "HEALTH_STATUS", "MODEL_NAME", "MODEL_VERSION", "FLEET_NAME", "OPERATING_CONDITION_DESC",
                "FAULT_MODES", "SENSOR_SYMBOL", "SENSOR_DESCRIPTION", "UNIT_OF_MEASURE",
                "CHECK_NAME", "CATEGORY", "STATUS"
            },
            WholeNumberColumns = {
                "UNIT_NUMBER", "CYCLE", "CURRENT_CYCLE", "ACTUAL_RUL", "SENSOR_ID",
                "OPERATING_CONDITIONS", "FAULT_MODE_COUNT", "FAILING_ROWS"
            },
            LogicalColumns = {"USED_IN_BASELINE_MODEL"},
            DateTimeColumns = {"CHECKED_AT"},
            DecimalColumns = List.Difference(
                Columns, TextColumns & WholeNumberColumns & LogicalColumns & DateTimeColumns
            ),

            TypeList =
                List.Transform(List.Intersect({Columns, TextColumns}), each {_, type text})
                & List.Transform(List.Intersect({Columns, WholeNumberColumns}), each {_, Int64.Type})
                & List.Transform(List.Intersect({Columns, LogicalColumns}), each {_, type logical})
                & List.Transform(List.Intersect({Columns, DateTimeColumns}), each {_, type datetime})
                & List.Transform(DecimalColumns, each {_, type number}),
            Typed = Table.TransformColumnTypes(Promoted, TypeList, "en-US")
        in
            Typed,

    FromSnowflake = () =>
        let
            Source = Snowflake.Databases(SnowflakeServer, "ENGINE_WH", [Role = "ENGINE_ANALYST"]),
            Database = Source{[Name = "ENGINE_ANALYTICS", Kind = "Database"]}[Data],
            Schema = Database{[Name = "ANALYTICS", Kind = "Schema"]}[Data],
            Result = Schema{[Name = tableName]}[Data]
        in
            Result
in
    if SourceMode = "Snowflake" then FromSnowflake() else FromCsv()
