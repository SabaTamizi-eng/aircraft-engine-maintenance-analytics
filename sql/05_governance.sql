-- Serial number masking and row access by fleet (needs Enterprise edition).
-- Using CURRENT_ROLE() instead of IS_ROLE_IN_SESSION(): the latter also counts
-- secondary roles, so a user with all three roles would always see everything.

USE ROLE ENGINE_ENGINEER;
USE WAREHOUSE ENGINE_WH;
USE SCHEMA ENGINE_ANALYTICS.ANALYTICS;

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

CREATE MASKING POLICY IF NOT EXISTS MP_ENGINE_SERIAL AS (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('ENGINE_ENGINEER', 'ENGINE_ANALYST', 'ACCOUNTADMIN', 'SYSADMIN') THEN val
        ELSE 'ESN-*****' || RIGHT(val, 4)
    END;

CREATE ROW ACCESS POLICY IF NOT EXISTS RAP_FLEET AS (p_fleet_id VARCHAR) RETURNS BOOLEAN ->
    CURRENT_ROLE() IN ('ENGINE_ENGINEER', 'ENGINE_ANALYST', 'ACCOUNTADMIN', 'SYSADMIN')
    OR EXISTS (
        SELECT 1
        FROM ENGINE_ANALYTICS.ANALYTICS.FLEET_ACCESS_MAP m
        WHERE m.role_name = CURRENT_ROLE()
          AND m.fleet_id = p_fleet_id
    );

-- FORCE / DROP ALL so this file can be re-run
ALTER TABLE DIM_ENGINE MODIFY COLUMN engine_serial_number SET MASKING POLICY MP_ENGINE_SERIAL FORCE;

ALTER TABLE DIM_ENGINE DROP ALL ROW ACCESS POLICIES;
ALTER TABLE DIM_ENGINE ADD ROW ACCESS POLICY RAP_FLEET ON (fleet_id);

ALTER TABLE FACT_ENGINE_CYCLE DROP ALL ROW ACCESS POLICIES;
ALTER TABLE FACT_ENGINE_CYCLE ADD ROW ACCESS POLICY RAP_FLEET ON (fleet_id);

-- check: as ENGINE_ANALYST you should get 4 fleets with full serials,
-- as ENGINE_FLEET_VIEWER only FD001 and FD003 with masked serials
-- SELECT fleet_id, COUNT(*), MIN(engine_serial_number)
-- FROM ENGINE_ANALYTICS.ANALYTICS.DIM_ENGINE GROUP BY fleet_id ORDER BY fleet_id;
