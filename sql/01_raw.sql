/* =============================================================================
   01_raw.sql
   Landing layer: file format, internal stage, raw tables and the CDC stream.
   Column order must match pipeline/config.py (CYCLE_COLUMNS, TRUTH_COLUMNS,
   PREDICTION_COLUMNS).
   ============================================================================= */
USE ROLE ENGINE_ENGINEER;
USE WAREHOUSE ENGINE_WH;
USE SCHEMA ENGINE_ANALYTICS.RAW;

CREATE FILE FORMAT IF NOT EXISTS CSV_FF
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  EMPTY_FIELD_AS_NULL = TRUE;

CREATE STAGE IF NOT EXISTS ENGINE_STAGE
  FILE_FORMAT = CSV_FF
  COMMENT = 'Internal stage for pipeline files';

-- One row per engine per operating cycle, exactly as delivered (append-only)
CREATE TABLE IF NOT EXISTS ENGINE_CYCLES_RAW (
    fleet_id        VARCHAR(5)   NOT NULL,   -- FD001 to FD004
    dataset_split   VARCHAR(5)   NOT NULL,   -- 'train' (run to failure) or 'test' (in service)
    unit_number     NUMBER(5,0)  NOT NULL,
    cycle           NUMBER(5,0)  NOT NULL,
    op_setting_1    FLOAT, op_setting_2  FLOAT, op_setting_3  FLOAT,
    sensor_1        FLOAT, sensor_2  FLOAT, sensor_3  FLOAT, sensor_4  FLOAT, sensor_5  FLOAT,
    sensor_6        FLOAT, sensor_7  FLOAT, sensor_8  FLOAT, sensor_9  FLOAT, sensor_10 FLOAT,
    sensor_11       FLOAT, sensor_12 FLOAT, sensor_13 FLOAT, sensor_14 FLOAT, sensor_15 FLOAT,
    sensor_16       FLOAT, sensor_17 FLOAT, sensor_18 FLOAT, sensor_19 FLOAT, sensor_20 FLOAT,
    sensor_21       FLOAT,
    source_file     VARCHAR,
    loaded_at       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Failure reference per engine (full reload each time)
CREATE TABLE IF NOT EXISTS ENGINE_RUL_TRUTH (
    fleet_id            VARCHAR(5)  NOT NULL,
    dataset_split       VARCHAR(5)  NOT NULL,
    unit_number         NUMBER(5,0) NOT NULL,
    final_cycle         NUMBER(5,0) NOT NULL,  -- last cycle in the full NASA file
    rul_at_final_cycle  NUMBER(5,0) NOT NULL,  -- 0 for run-to-failure engines, NASA truth for in-service
    loaded_at           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Remaining useful life predictions from ml/train_rul_model.py (full reload each time)
CREATE TABLE IF NOT EXISTS RUL_PREDICTIONS_RAW (
    fleet_id        VARCHAR(5)  NOT NULL,
    dataset_split   VARCHAR(5)  NOT NULL,
    unit_number     NUMBER(5,0) NOT NULL,
    cycle           NUMBER(5,0) NOT NULL,     -- cycle the prediction was made at
    predicted_rul   FLOAT       NOT NULL,
    model_name      VARCHAR,
    model_version   VARCHAR,
    loaded_at       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Change data capture: the stream records every row appended to the landing table
-- since it was last consumed. Created before the first load so history flows through it too.
CREATE STREAM IF NOT EXISTS ENGINE_CYCLES_STREAM
  ON TABLE ENGINE_CYCLES_RAW
  APPEND_ONLY = TRUE
  COMMENT = 'New engine cycles waiting to be merged into ANALYTICS';
