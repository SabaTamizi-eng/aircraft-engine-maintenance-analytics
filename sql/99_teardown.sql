/* =============================================================================
   99_teardown.sql
   Remove everything this project created (for example, before a trial ends).
   This permanently deletes the data. Run as ACCOUNTADMIN.
   ============================================================================= */
USE ROLE ACCOUNTADMIN;

ALTER TASK IF EXISTS ENGINE_ANALYTICS.ANALYTICS.TASK_PROCESS_ENGINE_CYCLES SUSPEND;
DROP DATABASE IF EXISTS ENGINE_ANALYTICS;
DROP WAREHOUSE IF EXISTS ENGINE_WH;
DROP ROLE IF EXISTS ENGINE_FLEET_VIEWER;
DROP ROLE IF EXISTS ENGINE_ANALYST;
DROP ROLE IF EXISTS ENGINE_ENGINEER;
