-- ======================================================================
-- RAW tcz_37526b20.base_table_assignment - BAGIAN 02/04
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`data4`,
    t.`data5`,
    t.`data6`,
    t.`data7`,
    t.`data8`,
    t.`data9`,
    t.`date_created`,
    t.`date_modified`,
    t.`done`,
    t.`external_done`,
    t.`is_target`,
    t.`is_tarik_sample`,
    t.`latitude`,
    t.`level_1_code`,
    t.`level_1_name`,
    t.`level_10_code`,
    t.`level_10_full_code`,
    t.`level_10_name`,
    t.`level_2_code`,
    t.`level_2_name`,
    t.`level_3_code`,
    t.`level_3_full_code`,
    t.`level_3_name`
FROM tcz_37526b20.base_table_assignment t
WHERE t.is_active = 1
  AND t.level_2_full_code = '6502'
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
