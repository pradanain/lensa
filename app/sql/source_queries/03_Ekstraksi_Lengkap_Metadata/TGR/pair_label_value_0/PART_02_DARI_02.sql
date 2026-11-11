-- ======================================================================
-- RAW tgr_fd68e454.pair_label_value_0 - BAGIAN 02/02
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, data_key, pair_label, pair_value
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`data_key`,
    t.`pair_label`,
    t.`pair_value`,
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
    t.`survey_period_id`,
    t.`survey_period_name`
FROM tgr_fd68e454.pair_label_value_0 t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
