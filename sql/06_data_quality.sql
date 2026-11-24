/* =============================================================================
   06_data_quality.sql
   Automated data quality checks, exposed as a view for the dashboard.
   failing_rows = 0 means the check passed.
   ============================================================================= */
USE ROLE ENGINE_ENGINEER;
USE WAREHOUSE ENGINE_WH;
USE SCHEMA ENGINE_ANALYTICS.ANALYTICS;

CREATE OR REPLACE VIEW VW_DATA_QUALITY_CHECKS AS
WITH checks AS (
    SELECT 'Fact table is up to date with raw data' AS check_name,
           'Completeness' AS category,
           (SELECT COUNT(*) FROM ENGINE_ANALYTICS.STAGING.STG_ENGINE_CYCLES)
         - (SELECT COUNT(*) FROM ENGINE_ANALYTICS.ANALYTICS.FACT_ENGINE_CYCLE) AS failing_rows

    UNION ALL
    SELECT 'No duplicate engine cycles', 'Uniqueness', COUNT(*)
    FROM (
        SELECT engine_key, cycle
        FROM ENGINE_ANALYTICS.ANALYTICS.FACT_ENGINE_CYCLE
        GROUP BY engine_key, cycle
        HAVING COUNT(*) > 1
    )

    UNION ALL
    -- ARRAY_CONSTRUCT_COMPACT drops NULLs, so fewer than 21 values means a missing reading
    SELECT 'No missing sensor readings', 'Completeness',
           COUNT_IF(ARRAY_SIZE(ARRAY_CONSTRUCT_COMPACT(
               sensor_1, sensor_2, sensor_3, sensor_4, sensor_5, sensor_6, sensor_7,
               sensor_8, sensor_9, sensor_10, sensor_11, sensor_12, sensor_13, sensor_14,
               sensor_15, sensor_16, sensor_17, sensor_18, sensor_19, sensor_20, sensor_21
           )) < 21)
    FROM ENGINE_ANALYTICS.ANALYTICS.FACT_ENGINE_CYCLE

    UNION ALL
    SELECT 'Cycles are continuous from 1 for every engine', 'Consistency', COUNT(*)
    FROM (
        SELECT engine_key
        FROM ENGINE_ANALYTICS.ANALYTICS.FACT_ENGINE_CYCLE
        GROUP BY engine_key
        HAVING MIN(cycle) <> 1 OR MAX(cycle) - MIN(cycle) + 1 <> COUNT(*)
    )

    UNION ALL
    SELECT 'Every fact row has an engine', 'Referential integrity', COUNT(*)
    FROM ENGINE_ANALYTICS.ANALYTICS.FACT_ENGINE_CYCLE f
    LEFT JOIN ENGINE_ANALYTICS.ANALYTICS.DIM_ENGINE d ON d.engine_key = f.engine_key
    WHERE d.engine_key IS NULL

    UNION ALL
    SELECT 'Every engine has a failure reference', 'Referential integrity', COUNT(*)
    FROM ENGINE_ANALYTICS.ANALYTICS.DIM_ENGINE d
    LEFT JOIN ENGINE_ANALYTICS.STAGING.STG_ENGINE_RUL_TRUTH t ON t.engine_key = d.engine_key
    WHERE t.engine_key IS NULL

    UNION ALL
    SELECT 'No cycle beyond the engine failure point', 'Validity', COUNT(*)
    FROM ENGINE_ANALYTICS.ANALYTICS.VW_ENGINE_CYCLE_RUL
    WHERE actual_rul < 0

    UNION ALL
    -- Temperatures are in degrees Rankine, so they must be positive
    SELECT 'Temperature sensors within physical range', 'Validity',
           COUNT_IF(sensor_1 <= 0 OR sensor_2 <= 0 OR sensor_3 <= 0 OR sensor_4 <= 0)
    FROM ENGINE_ANALYTICS.ANALYTICS.FACT_ENGINE_CYCLE
)
SELECT
    check_name,
    category,
    failing_rows,
    IFF(failing_rows = 0, 'PASS', 'FAIL') AS status,
    CURRENT_TIMESTAMP() AS checked_at
FROM checks;

-- SELECT * FROM ENGINE_ANALYTICS.ANALYTICS.VW_DATA_QUALITY_CHECKS ORDER BY status, category;
