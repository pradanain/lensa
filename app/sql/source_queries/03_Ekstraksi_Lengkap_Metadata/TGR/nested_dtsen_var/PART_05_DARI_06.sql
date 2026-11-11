-- ======================================================================
-- RAW tgr_fd68e454.nested_dtsen_var - BAGIAN 05/06
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`assignment_status_id`,
    t.`is_active`,
    t.`level_1_code`,
    t.`level_1_name`,
    t.`level_10_code`,
    t.`level_10_full_code`,
    t.`level_10_name`,
    t.`level_2_code`,
    t.`level_2_name`,
    t.`level_3_code`,
    t.`level_3_full_code`,
    t.`level_3_name`,
    t.`level_4_code`,
    t.`level_4_full_code`,
    t.`level_4_name`,
    t.`level_5_code`,
    t.`level_5_full_code`,
    t.`level_5_name`,
    t.`level_6_code`,
    t.`level_6_full_code`,
    t.`level_6_name`
FROM tgr_fd68e454.nested_dtsen_var t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
