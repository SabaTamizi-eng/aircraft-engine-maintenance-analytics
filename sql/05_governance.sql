/* =============================================================================
   05_governance.sql
   Data governance: column masking for engine serial numbers and row-level
   security by fleet. Requires Snowflake Enterprise edition (choose it when you
   start the free trial).

   Policies use CURRENT_ROLE() (the role selected for the session) rather than
   IS_ROLE_IN_SESSION(), so results stay predictable when a user also has other
   roles active as secondary roles.
   ============================================================================= */
USE ROLE ENGINE_ENGINEER;
USE WAREHOUSE ENGINE_WH;
USE SCHEMA ENGINE_ANALYTICS.ANALYTICS;

-- Which restricted roles may see which fleets
CREATE TABLE IF NOT EXISTS FLEET_ACCESS_MAP (
    role_name  VARCHAR    NOT NULL,
    fleet_id   VARCHAR(5) NOT NULL
);

MERGE INTO FLEET_ACCESS_MAP t
USING (
    SELECT column1 AS role_name, column2 AS fleet_id
    FROM VALUES ('ENGINE_FLEET_VIEWER', 'FD001'), ('ENGINE_FLEET_VIEWER', 'FD003')
) s
ON t.role_name = s.role_name AND t.fleet_id = s.fleet_id
WHEN NOT MATCHED THEN INSERT (role_name, fleet_id) VALUES (s.role_name, s.fleet_id);

-- Column masking: only engineering and analyst roles see full serial numbers
CREATE MASKING POLICY IF NOT EXISTS MP_ENGINE_SERIAL AS (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('ENGINE_ENGINEER', 'ENGINE_ANALYST', 'ACCOUNTADMIN', 'SYSADMIN') THEN val
        ELSE 'ESN-*****' || RIGHT(val, 4)
    END;

-- Row-level security: full access for engineering/analyst roles, mapped fleets for others
CREATE ROW ACCESS POLICY IF NOT EXISTS RAP_FLEET AS (p_fleet_id VARCHAR) RETURNS BOOLEAN ->
    CURRENT_ROLE() IN ('ENGINE_ENGINEER', 'ENGINE_ANALYST', 'ACCOUNTADMIN', 'SYSADMIN')
    OR EXISTS (
        SELECT 1
        FROM ENGINE_ANALYTICS.ANALYTICS.FLEET_ACCESS_MAP m
        WHERE m.role_name = CURRENT_ROLE()
          AND m.fleet_id = p_fleet_id
    );

-- Attach the policies (safe to re-run)
ALTER TABLE DIM_ENGINE MODIFY COLUMN engine_serial_number SET MASKING POLICY MP_ENGINE_SERIAL FORCE;

ALTER TABLE DIM_ENGINE DROP ALL ROW ACCESS POLICIES;
ALTER TABLE DIM_ENGINE ADD ROW ACCESS POLICY RAP_FLEET ON (fleet_id);

ALTER TABLE FACT_ENGINE_CYCLE DROP ALL ROW ACCESS POLICIES;
ALTER TABLE FACT_ENGINE_CYCLE ADD ROW ACCESS POLICY RAP_FLEET ON (fleet_id);

/* Try it (views built on these tables inherit the policies)
   USE ROLE ENGINE_ANALYST;
   SELECT fleet_id, COUNT(*) AS engines, MIN(engine_serial_number) AS sample_serial
   FROM ENGINE_ANALYTICS.ANALYTICS.DIM_ENGINE GROUP BY fleet_id ORDER BY fleet_id;
   -- 4 fleets, full serial numbers

   USE ROLE ENGINE_FLEET_VIEWER;
   SELECT fleet_id, COUNT(*) AS engines, MIN(engine_serial_number) AS sample_serial
   FROM ENGINE_ANALYTICS.ANALYTICS.DIM_ENGINE GROUP BY fleet_id ORDER BY fleet_id;
   -- FD001 and FD003 only, masked serial numbers
*/
