-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 13/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`ya_gabung`,
    t.`skala_usaha_prelist`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`assignment_listing`,
    t.`assignment_status_alias`,
    t.`assignment_status_id`,
    t.`desa_prelist`,
    t.`desa_prelist_loaded`,
    t.`is_active`,
    t.`kec_prelist`,
    t.`kec_prelist_loaded`,
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
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
