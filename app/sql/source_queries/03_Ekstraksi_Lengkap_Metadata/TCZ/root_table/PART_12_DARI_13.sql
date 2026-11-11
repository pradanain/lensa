-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 12/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
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
    t.`pusat_nested`,
    t.`survey_period_id`,
    t.`survey_period_name`,
    t.`list_kbli_halal`,
    t.`panduan_genai`,
    t.`list_kbli_bpom`,
    t.`total_pendapatan_float`,
    t.`aset_total_float`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
