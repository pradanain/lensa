-- ======================================================================
-- RAW tgr_fd68e454.base_table_assignment - BAGIAN 04/04
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`source_from`,
    t.`strata`,
    t.`substituted_by`,
    t.`substituted_for`,
    t.`substituted_with`,
    t.`sum_clean`,
    t.`sum_error`,
    t.`sum_remark`,
    t.`survey_period_id`,
    t.`survey_period_name`,
    t.`user_id_responsibility`
FROM tgr_fd68e454.base_table_assignment t
WHERE t.is_active = 1
  AND t.level_2_full_code = '6502'
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
