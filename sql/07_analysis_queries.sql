/* =============================================================================
   07_analysis_queries.sql
   Example analysis queries (window functions, regression, percentiles).
   Run as ENGINE_ANALYST or ENGINE_ENGINEER.
   ============================================================================= */
USE WAREHOUSE ENGINE_WH;
USE SCHEMA ENGINE_ANALYTICS.ANALYTICS;

-- 1) In-service engines closest to failure: the maintenance planning list
SELECT h.engine_key, f.fleet_name, h.current_cycle, h.actual_rul, h.predicted_rul, h.health_status
FROM VW_ENGINE_CURRENT_HEALTH h
JOIN DIM_FLEET f ON f.fleet_id = h.fleet_id
WHERE h.engine_lifecycle = 'In service'
ORDER BY h.actual_rul
LIMIT 15;

-- 2) Cycles to failure by fleet: how long engines last under each operating profile
WITH life AS (
    SELECT d.fleet_id, d.engine_key, MAX(c.cycle) AS cycles_to_failure
    FROM FACT_ENGINE_CYCLE c
    JOIN DIM_ENGINE d ON d.engine_key = c.engine_key
    WHERE d.engine_lifecycle = 'Run to failure'
    GROUP BY d.fleet_id, d.engine_key
)
SELECT
    fleet_id,
    COUNT(*)                                                       AS engines,
    ROUND(AVG(cycles_to_failure))                                  AS avg_cycles,
    PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY cycles_to_failure) AS p10_cycles,
    MEDIAN(cycles_to_failure)                                      AS median_cycles,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY cycles_to_failure) AS p90_cycles
FROM life
GROUP BY fleet_id
ORDER BY fleet_id;

-- 3) Which sensors drift most as engines wear out? Slope of each sensor against cycle,
--    over the last 50 cycles before failure, for fleet FD001
SELECT
    s.sensor_symbol,
    s.sensor_description,
    ROUND(REGR_SLOPE(r.reading, r.cycle), 5)          AS avg_change_per_cycle,
    ROUND(CORR(r.reading, -v.actual_rul), 3)          AS correlation_with_wear
FROM VW_SENSOR_READINGS_LONG r
JOIN VW_ENGINE_CYCLE_RUL v ON v.engine_key = r.engine_key AND v.cycle = r.cycle
JOIN DIM_SENSOR s ON s.sensor_id = r.sensor_id
JOIN DIM_ENGINE d ON d.engine_key = r.engine_key
WHERE d.fleet_id = 'FD001'
  AND d.engine_lifecycle = 'Run to failure'
  AND v.actual_rul <= 50
GROUP BY s.sensor_symbol, s.sensor_description
HAVING STDDEV(r.reading) > 0
ORDER BY ABS(correlation_with_wear) DESC;

-- 4) Smoothed trend for one engine: 10-cycle moving average of HPC outlet temperature (T30)
SELECT
    engine_key,
    cycle,
    sensor_3 AS t30,
    AVG(sensor_3) OVER (PARTITION BY engine_key ORDER BY cycle ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS t30_moving_avg_10,
    actual_rul
FROM VW_ENGINE_CYCLE_RUL
WHERE engine_key = 'FD001-TRAIN-001'
ORDER BY cycle;

-- 5) Model accuracy by health band (only engines with a prediction)
SELECT
    health_status,
    COUNT(*)                                        AS engines,
    ROUND(SQRT(AVG(POWER(prediction_error, 2))), 1) AS rmse_cycles,
    ROUND(AVG(ABS(prediction_error)), 1)            AS mae_cycles,
    COUNT_IF(prediction_error > 10)                 AS predicted_too_late
FROM VW_ENGINE_CURRENT_HEALTH
WHERE predicted_rul IS NOT NULL
GROUP BY health_status
ORDER BY rmse_cycles DESC;
