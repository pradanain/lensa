-- ======================================================================
-- RAW tgr_fd68e454.nested_dtsen - BAGIAN 04/04
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`level_9_name`,
    t.`survey_period_id`,
    t.`survey_period_name`
FROM tgr_fd68e454.nested_dtsen t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
