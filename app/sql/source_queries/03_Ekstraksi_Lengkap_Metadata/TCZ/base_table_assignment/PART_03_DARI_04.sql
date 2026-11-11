-- ======================================================================
-- RAW tcz_37526b20.base_table_assignment - BAGIAN 03/04
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`level_4_code`,
    t.`level_4_full_code`,
    t.`level_4_name`,
    t.`level_5_code`,
    t.`level_5_full_code`,
    t.`level_5_name`,
    t.`level_6_code`,
    t.`level_6_full_code`,
    t.`level_6_name`,
    t.`level_7_code`,
    t.`level_7_full_code`,
    t.`level_7_name`,
    t.`level_8_code`,
    t.`level_8_full_code`,
    t.`level_8_name`,
    t.`level_9_code`,
    t.`level_9_full_code`,
    t.`level_9_name`,
    t.`listing`,
    t.`longitude`,
    t.`referenced_id`,
    t.`sample_type`,
    t.`secondary`
FROM tcz_37526b20.base_table_assignment t
WHERE t.is_active = 1
  AND t.level_2_full_code = '6502'
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
