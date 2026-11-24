/* =============================================================================
   02_staging.sql
   Cleaned, de-duplicated views over the raw tables, plus one shared definition
   of the engine business key.
   ============================================================================= */
USE ROLE ENGINE_ENGINEER;
USE WAREHOUSE ENGINE_WH;
USE SCHEMA ENGINE_ANALYTICS.STAGING;

-- Engine business key, e.g. FD001-TRAIN-007. Defined once and reused everywhere.
CREATE OR REPLACE FUNCTION FN_ENGINE_KEY(fleet_id VARCHAR, dataset_split VARCHAR, unit_number NUMBER)
RETURNS VARCHAR
AS
$$
    fleet_id || '-' || UPPER(dataset_split) || '-' || LPAD(unit_number::VARCHAR, 3, '0')
$$;

-- Latest version of each engine cycle (a re-delivered cycle replaces the earlier one)
CREATE OR REPLACE VIEW STG_ENGINE_CYCLES AS
SELECT
    ENGINE_ANALYTICS.STAGING.FN_ENGINE_KEY(fleet_id, dataset_split, unit_number) AS engine_key,
    * EXCLUDE (source_file)
FROM ENGINE_ANALYTICS.RAW.ENGINE_CYCLES_RAW
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY fleet_id, dataset_split, unit_number, cycle
    ORDER BY loaded_at DESC
) = 1;

-- Failure reference. failure_cycle = the cycle at which the engine fails (or would fail).
CREATE OR REPLACE VIEW STG_ENGINE_RUL_TRUTH AS
SELECT
    ENGINE_ANALYTICS.STAGING.FN_ENGINE_KEY(fleet_id, dataset_split, unit_number) AS engine_key,
    fleet_id,
    dataset_split,
    unit_number,
    final_cycle,
    rul_at_final_cycle,
    final_cycle + rul_at_final_cycle AS failure_cycle
FROM ENGINE_ANALYTICS.RAW.ENGINE_RUL_TRUTH;

-- Latest prediction per engine and cycle
CREATE OR REPLACE VIEW STG_RUL_PREDICTIONS AS
SELECT
    ENGINE_ANALYTICS.STAGING.FN_ENGINE_KEY(fleet_id, dataset_split, unit_number) AS engine_key,
    fleet_id,
    dataset_split,
    unit_number,
    cycle,
    ROUND(predicted_rul, 1) AS predicted_rul,
    model_name,
    model_version,
    loaded_at
FROM ENGINE_ANALYTICS.RAW.RUL_PREDICTIONS_RAW
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY fleet_id, dataset_split, unit_number, cycle
    ORDER BY loaded_at DESC
) = 1;
