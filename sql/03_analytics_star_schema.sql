/* =============================================================================
   03_analytics_star_schema.sql
   Star schema (dimensions + fact) and the reporting views used by Power BI.
   Tables are filled incrementally by the task in 04_cdc_streams_tasks.sql.

   DIM_FLEET 1--* DIM_ENGINE 1--* FACT_ENGINE_CYCLE
   DIM_SENSOR 1--* VW_SENSOR_READINGS_LONG
   ============================================================================= */
USE ROLE ENGINE_ENGINEER;
USE WAREHOUSE ENGINE_WH;
USE SCHEMA ENGINE_ANALYTICS.ANALYTICS;

-- ---------------------------------------------------------------------------
-- Dimensions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS DIM_FLEET (
    fleet_id                  VARCHAR(5) NOT NULL,
    fleet_name                VARCHAR    NOT NULL,
    operating_conditions      NUMBER(2,0),
    operating_condition_desc  VARCHAR,
    fault_modes               VARCHAR,
    fault_mode_count          NUMBER(1,0),
    CONSTRAINT pk_dim_fleet PRIMARY KEY (fleet_id)
);

MERGE INTO DIM_FLEET t
USING (
    SELECT column1 AS fleet_id, column2 AS fleet_name, column3 AS operating_conditions,
           column4 AS operating_condition_desc, column5 AS fault_modes, column6 AS fault_mode_count
    FROM VALUES
        ('FD001', 'Fleet 1: sea level, HPC wear',            1, 'Sea level',             'HPC degradation',         1),
        ('FD002', 'Fleet 2: six conditions, HPC wear',       6, 'Six flight conditions', 'HPC degradation',         1),
        ('FD003', 'Fleet 3: sea level, HPC and fan wear',    1, 'Sea level',             'HPC and fan degradation', 2),
        ('FD004', 'Fleet 4: six conditions, HPC and fan wear', 6, 'Six flight conditions', 'HPC and fan degradation', 2)
) s
ON t.fleet_id = s.fleet_id
WHEN MATCHED THEN UPDATE SET
    fleet_name = s.fleet_name, operating_conditions = s.operating_conditions,
    operating_condition_desc = s.operating_condition_desc,
    fault_modes = s.fault_modes, fault_mode_count = s.fault_mode_count
WHEN NOT MATCHED THEN INSERT
    (fleet_id, fleet_name, operating_conditions, operating_condition_desc, fault_modes, fault_mode_count)
VALUES
    (s.fleet_id, s.fleet_name, s.operating_conditions, s.operating_condition_desc, s.fault_modes, s.fault_mode_count);

-- Sensor descriptions from Saxena et al. (2008), "Damage Propagation Modeling for
-- Aircraft Engine Run-to-Failure Simulation"
CREATE TABLE IF NOT EXISTS DIM_SENSOR (
    sensor_id               NUMBER(2,0) NOT NULL,
    sensor_symbol           VARCHAR(12),
    sensor_description      VARCHAR,
    unit_of_measure         VARCHAR(10),
    used_in_baseline_model  BOOLEAN,     -- sensors that change over an engine's life in FD001
    CONSTRAINT pk_dim_sensor PRIMARY KEY (sensor_id)
);

MERGE INTO DIM_SENSOR t
USING (
    SELECT column1 AS sensor_id, column2 AS sensor_symbol, column3 AS sensor_description,
           column4 AS unit_of_measure, column5 AS used_in_baseline_model
    FROM VALUES
        ( 1, 'T2',        'Total temperature at fan inlet',      'deg R',   FALSE),
        ( 2, 'T24',       'Total temperature at LPC outlet',     'deg R',   TRUE),
        ( 3, 'T30',       'Total temperature at HPC outlet',     'deg R',   TRUE),
        ( 4, 'T50',       'Total temperature at LPT outlet',     'deg R',   TRUE),
        ( 5, 'P2',        'Pressure at fan inlet',               'psia',    FALSE),
        ( 6, 'P15',       'Total pressure in bypass duct',       'psia',    FALSE),
        ( 7, 'P30',       'Total pressure at HPC outlet',        'psia',    TRUE),
        ( 8, 'Nf',        'Physical fan speed',                  'rpm',     TRUE),
        ( 9, 'Nc',        'Physical core speed',                 'rpm',     TRUE),
        (10, 'epr',       'Engine pressure ratio (P50/P2)',      'ratio',   FALSE),
        (11, 'Ps30',      'Static pressure at HPC outlet',       'psia',    TRUE),
        (12, 'phi',       'Ratio of fuel flow to Ps30',          'pps/psi', TRUE),
        (13, 'NRf',       'Corrected fan speed',                 'rpm',     TRUE),
        (14, 'NRc',       'Corrected core speed',                'rpm',     TRUE),
        (15, 'BPR',       'Bypass ratio',                        'ratio',   TRUE),
        (16, 'farB',      'Burner fuel-air ratio',               'ratio',   FALSE),
        (17, 'htBleed',   'Bleed enthalpy',                      'index',   TRUE),
        (18, 'Nf_dmd',    'Demanded fan speed',                  'rpm',     FALSE),
        (19, 'PCNfR_dmd', 'Demanded corrected fan speed',        'rpm',     FALSE),
        (20, 'W31',       'HPT coolant bleed',                   'lbm/s',   TRUE),
        (21, 'W32',       'LPT coolant bleed',                   'lbm/s',   TRUE)
) s
ON t.sensor_id = s.sensor_id
WHEN MATCHED THEN UPDATE SET
    sensor_symbol = s.sensor_symbol, sensor_description = s.sensor_description,
    unit_of_measure = s.unit_of_measure, used_in_baseline_model = s.used_in_baseline_model
WHEN NOT MATCHED THEN INSERT
    (sensor_id, sensor_symbol, sensor_description, unit_of_measure, used_in_baseline_model)
VALUES
    (s.sensor_id, s.sensor_symbol, s.sensor_description, s.unit_of_measure, s.used_in_baseline_model);

CREATE TABLE IF NOT EXISTS DIM_ENGINE (
    engine_key            VARCHAR(20) NOT NULL,   -- e.g. FD001-TEST-042
    engine_serial_number  VARCHAR(20),            -- synthetic; masked for restricted roles (05)
    fleet_id              VARCHAR(5)  NOT NULL,
    dataset_split         VARCHAR(5)  NOT NULL,
    unit_number           NUMBER(5,0) NOT NULL,
    engine_lifecycle      VARCHAR(20),            -- 'Run to failure' or 'In service'
    first_loaded_at       TIMESTAMP_NTZ,
    CONSTRAINT pk_dim_engine PRIMARY KEY (engine_key),
    CONSTRAINT fk_engine_fleet FOREIGN KEY (fleet_id) REFERENCES DIM_FLEET (fleet_id)
);

-- ---------------------------------------------------------------------------
-- Fact: one row per engine per operating cycle
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS FACT_ENGINE_CYCLE (
    engine_key        VARCHAR(20) NOT NULL,
    fleet_id          VARCHAR(5)  NOT NULL,     -- kept on the fact for row-level security
    cycle             NUMBER(5,0) NOT NULL,
    op_setting_1      FLOAT, op_setting_2  FLOAT, op_setting_3  FLOAT,
    sensor_1          FLOAT, sensor_2  FLOAT, sensor_3  FLOAT, sensor_4  FLOAT, sensor_5  FLOAT,
    sensor_6          FLOAT, sensor_7  FLOAT, sensor_8  FLOAT, sensor_9  FLOAT, sensor_10 FLOAT,
    sensor_11         FLOAT, sensor_12 FLOAT, sensor_13 FLOAT, sensor_14 FLOAT, sensor_15 FLOAT,
    sensor_16         FLOAT, sensor_17 FLOAT, sensor_18 FLOAT, sensor_19 FLOAT, sensor_20 FLOAT,
    sensor_21         FLOAT,
    source_loaded_at  TIMESTAMP_NTZ,
    processed_at      TIMESTAMP_NTZ,
    CONSTRAINT pk_fact_engine_cycle PRIMARY KEY (engine_key, cycle),
    CONSTRAINT fk_cycle_engine FOREIGN KEY (engine_key) REFERENCES DIM_ENGINE (engine_key)
);

-- ---------------------------------------------------------------------------
-- Reporting views (Power BI reads these)
-- ---------------------------------------------------------------------------

-- Every cycle with the actual remaining useful life (RUL) and a health band.
-- Bands: Critical <= 30 cycles, Warning <= 75 cycles, otherwise Healthy.
CREATE OR REPLACE VIEW VW_ENGINE_CYCLE_RUL AS
SELECT
    f.* EXCLUDE (source_loaded_at, processed_at),
    t.failure_cycle - f.cycle AS actual_rul,
    CASE
        WHEN t.failure_cycle - f.cycle <= 30 THEN 'Critical'
        WHEN t.failure_cycle - f.cycle <= 75 THEN 'Warning'
        ELSE 'Healthy'
    END AS health_status
FROM ENGINE_ANALYTICS.ANALYTICS.FACT_ENGINE_CYCLE f
JOIN ENGINE_ANALYTICS.STAGING.STG_ENGINE_RUL_TRUTH t
  ON t.engine_key = f.engine_key;

-- One row per engine at its latest loaded cycle, with the model prediction when available
CREATE OR REPLACE VIEW VW_ENGINE_CURRENT_HEALTH AS
WITH latest AS (
    SELECT engine_key, fleet_id, cycle AS current_cycle, actual_rul, health_status
    FROM ENGINE_ANALYTICS.ANALYTICS.VW_ENGINE_CYCLE_RUL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY engine_key ORDER BY cycle DESC) = 1
)
SELECT
    l.engine_key,
    l.fleet_id,
    d.dataset_split,
    d.engine_lifecycle,
    l.current_cycle,
    l.actual_rul,
    l.health_status,
    p.predicted_rul,
    p.model_name,
    p.model_version,
    p.predicted_rul - l.actual_rul AS prediction_error   -- positive = predicted too late (riskier)
FROM latest l
JOIN ENGINE_ANALYTICS.ANALYTICS.DIM_ENGINE d
  ON d.engine_key = l.engine_key
LEFT JOIN ENGINE_ANALYTICS.STAGING.STG_RUL_PREDICTIONS p
  ON p.engine_key = l.engine_key
 AND p.cycle = l.current_cycle;

-- Sensor readings in long format (one row per engine, cycle and sensor) for trend charts
CREATE OR REPLACE VIEW VW_SENSOR_READINGS_LONG AS
SELECT
    engine_key,
    fleet_id,
    cycle,
    TO_NUMBER(SPLIT_PART(sensor_column, '_', 2)) AS sensor_id,
    reading
FROM (
    SELECT engine_key, fleet_id, cycle,
           sensor_1, sensor_2, sensor_3, sensor_4, sensor_5, sensor_6, sensor_7,
           sensor_8, sensor_9, sensor_10, sensor_11, sensor_12, sensor_13, sensor_14,
           sensor_15, sensor_16, sensor_17, sensor_18, sensor_19, sensor_20, sensor_21
    FROM ENGINE_ANALYTICS.ANALYTICS.FACT_ENGINE_CYCLE
)
UNPIVOT (reading FOR sensor_column IN (
    sensor_1, sensor_2, sensor_3, sensor_4, sensor_5, sensor_6, sensor_7,
    sensor_8, sensor_9, sensor_10, sensor_11, sensor_12, sensor_13, sensor_14,
    sensor_15, sensor_16, sensor_17, sensor_18, sensor_19, sensor_20, sensor_21
));
