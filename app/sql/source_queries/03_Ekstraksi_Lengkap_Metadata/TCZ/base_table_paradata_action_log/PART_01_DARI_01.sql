-- ======================================================================
-- RAW tcz_37526b20.base_table_paradata_action_log - BAGIAN 01/01
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, timestamp, action_log_index
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`timestamp`,
    t.`action_log_index`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`action`,
    t.`battery_info_battery_level`,
    t.`battery_info_battery_temperature`,
    t.`is_mock`,
    t.`latitude`,
    t.`longitude`,
    t.`user_id`,
    t.`user_name`
FROM tcz_37526b20.base_table_paradata_action_log t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
