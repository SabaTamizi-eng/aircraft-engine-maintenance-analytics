-- Merge new rows from the stream into the star schema.
-- The task runs every 5 minutes but skips when the stream is empty.

USE ROLE ENGINE_ENGINEER;
USE WAREHOUSE ENGINE_WH;
USE SCHEMA ENGINE_ANALYTICS.ANALYTICS;

CREATE OR REPLACE PROCEDURE SP_PROCESS_ENGINE_CYCLES()
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    new_engines   INTEGER DEFAULT 0;
    merged_cycles INTEGER DEFAULT 0;
BEGIN
    -- Both MERGEs read the stream. Inside one transaction they see the same rows,
    -- and the offset only moves on COMMIT.
    BEGIN TRANSACTION;

    -- new engines
    MERGE INTO ENGINE_ANALYTICS.ANALYTICS.DIM_ENGINE d
    USING (
        SELECT DISTINCT
            ENGINE_ANALYTICS.STAGING.FN_ENGINE_KEY(fleet_id, dataset_split, unit_number) AS engine_key,
            fleet_id,
            LOWER(dataset_split) AS dataset_split,
            unit_number
        FROM ENGINE_ANALYTICS.RAW.ENGINE_CYCLES_STREAM
        WHERE METADATA$ACTION = 'INSERT'
    ) s
    ON d.engine_key = s.engine_key
    WHEN NOT MATCHED THEN INSERT
        (engine_key, engine_serial_number, fleet_id, dataset_split, unit_number, engine_lifecycle, first_loaded_at)
    VALUES (
        s.engine_key,
        'ESN-' || SUBSTR(s.fleet_id, 3) || '-' || IFF(s.dataset_split = 'train', 'R', 'S')
            || LPAD(s.unit_number::VARCHAR, 4, '0'),
        s.fleet_id,
        s.dataset_split,
        s.unit_number,
        IFF(s.dataset_split = 'train', 'Run to failure', 'In service'),
        CURRENT_TIMESTAMP()
    );
    new_engines := SQLROWCOUNT;

    -- cycles (latest delivery wins)
    MERGE INTO ENGINE_ANALYTICS.ANALYTICS.FACT_ENGINE_CYCLE f
    USING (
        SELECT
            ENGINE_ANALYTICS.STAGING.FN_ENGINE_KEY(fleet_id, dataset_split, unit_number) AS engine_key,
            fleet_id, cycle,
            op_setting_1, op_setting_2, op_setting_3,
            sensor_1, sensor_2, sensor_3, sensor_4, sensor_5, sensor_6, sensor_7,
            sensor_8, sensor_9, sensor_10, sensor_11, sensor_12, sensor_13, sensor_14,
            sensor_15, sensor_16, sensor_17, sensor_18, sensor_19, sensor_20, sensor_21,
            loaded_at
        FROM ENGINE_ANALYTICS.RAW.ENGINE_CYCLES_STREAM
        WHERE METADATA$ACTION = 'INSERT'
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY fleet_id, dataset_split, unit_number, cycle
            ORDER BY loaded_at DESC
        ) = 1
    ) s
    ON f.engine_key = s.engine_key AND f.cycle = s.cycle
    WHEN MATCHED THEN UPDATE SET
        op_setting_1 = s.op_setting_1, op_setting_2 = s.op_setting_2, op_setting_3 = s.op_setting_3,
        sensor_1  = s.sensor_1,  sensor_2  = s.sensor_2,  sensor_3  = s.sensor_3,  sensor_4  = s.sensor_4,
        sensor_5  = s.sensor_5,  sensor_6  = s.sensor_6,  sensor_7  = s.sensor_7,  sensor_8  = s.sensor_8,
        sensor_9  = s.sensor_9,  sensor_10 = s.sensor_10, sensor_11 = s.sensor_11, sensor_12 = s.sensor_12,
        sensor_13 = s.sensor_13, sensor_14 = s.sensor_14, sensor_15 = s.sensor_15, sensor_16 = s.sensor_16,
        sensor_17 = s.sensor_17, sensor_18 = s.sensor_18, sensor_19 = s.sensor_19, sensor_20 = s.sensor_20,
        sensor_21 = s.sensor_21,
        source_loaded_at = s.loaded_at,
        processed_at = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN INSERT (
        engine_key, fleet_id, cycle, op_setting_1, op_setting_2, op_setting_3,
        sensor_1, sensor_2, sensor_3, sensor_4, sensor_5, sensor_6, sensor_7,
        sensor_8, sensor_9, sensor_10, sensor_11, sensor_12, sensor_13, sensor_14,
        sensor_15, sensor_16, sensor_17, sensor_18, sensor_19, sensor_20, sensor_21,
        source_loaded_at, processed_at
    ) VALUES (
        s.engine_key, s.fleet_id, s.cycle, s.op_setting_1, s.op_setting_2, s.op_setting_3,
        s.sensor_1, s.sensor_2, s.sensor_3, s.sensor_4, s.sensor_5, s.sensor_6, s.sensor_7,
        s.sensor_8, s.sensor_9, s.sensor_10, s.sensor_11, s.sensor_12, s.sensor_13, s.sensor_14,
        s.sensor_15, s.sensor_16, s.sensor_17, s.sensor_18, s.sensor_19, s.sensor_20, s.sensor_21,
        s.loaded_at, CURRENT_TIMESTAMP()
    );
    merged_cycles := SQLROWCOUNT;

    COMMIT;
    RETURN 'New engines: ' || new_engines || ', cycles merged: ' || merged_cycles;
EXCEPTION
    WHEN OTHER THEN
        ROLLBACK;
        RAISE;
END;
$$;

CREATE OR REPLACE TASK TASK_PROCESS_ENGINE_CYCLES
  WAREHOUSE = ENGINE_WH
  SCHEDULE = '5 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('ENGINE_ANALYTICS.RAW.ENGINE_CYCLES_STREAM')
AS
  CALL ENGINE_ANALYTICS.ANALYTICS.SP_PROCESS_ENGINE_CYCLES();

ALTER TASK TASK_PROCESS_ENGINE_CYCLES RESUME;

-- EXECUTE TASK ANALYTICS.TASK_PROCESS_ENGINE_CYCLES;
-- SELECT SYSTEM$STREAM_HAS_DATA('ENGINE_ANALYTICS.RAW.ENGINE_CYCLES_STREAM');
-- SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(TASK_NAME => 'TASK_PROCESS_ENGINE_CYCLES'))
--   ORDER BY scheduled_time DESC LIMIT 10;
-- ALTER TASK ANALYTICS.TASK_PROCESS_ENGINE_CYCLES SUSPEND;
