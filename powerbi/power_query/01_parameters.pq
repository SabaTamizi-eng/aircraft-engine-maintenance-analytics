// Create these three parameters in Power Query (Home > Manage Parameters > New Parameter).
// All are Type = Text.

// SourceMode
//   "CSV"        read the local files in data/powerbi/ (no Snowflake account needed)
//   "Snowflake"  read the live views in ENGINE_ANALYTICS.ANALYTICS
"CSV" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]

// DataFolder: full path to data/powerbi/, ending with a backslash, for example
//   C:\Users\you\aircraft-engine-maintenance-analytics\data\powerbi\
// SnowflakeServer: your account URL without https://, for example
//   abc12345.ca-central-1.aws.snowflakecomputing.com
