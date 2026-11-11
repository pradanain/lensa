-- ======================================================================
-- RAW tcz_37526b20.base_table_assignment_history - BAGIAN 01/01
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, date_created
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`date_created`,
    t.`mode`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`assignment_id_date_created`,
    t.`remark`,
    t.`user_id`,
    t.`status_id`,
    t.`status_alias`
FROM tcz_37526b20.base_table_assignment_history t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
