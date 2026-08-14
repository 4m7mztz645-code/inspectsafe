-- Inspect Safe CLEAN START reset
-- WARNING: This permanently deletes all current Inspect Safe app data.
-- It keeps the database schema/tables so the app can start fresh.
-- Run this only against the Inspect Safe PostgreSQL database you intend to reset.

BEGIN;

TRUNCATE TABLE
    inspection_items,
    inspections,
    ride_checklist,
    maintenance_logs,
    accident_reports,
    ride_documents,
    login_log,
    rides,
    users,
    company,
    checklist
RESTART IDENTITY CASCADE;

COMMIT;
