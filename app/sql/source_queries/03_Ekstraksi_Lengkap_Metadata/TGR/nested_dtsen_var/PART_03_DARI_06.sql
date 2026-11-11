-- ======================================================================
-- RAW tgr_fd68e454.nested_dtsen_var - BAGIAN 03/06
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`sakit_rematik_label`,
    t.`sakit_rematik_value`,
    t.`sakit_asma_label`,
    t.`sakit_asma_value`,
    t.`sakit_jantung_label`,
    t.`sakit_jantung_value`,
    t.`sakit_diabetes_label`,
    t.`sakit_diabetes_value`,
    t.`sakit_tbc_label`,
    t.`sakit_tbc_value`,
    t.`sakit_stroke_label`,
    t.`sakit_stroke_value`,
    t.`sakit_kanker_label`,
    t.`sakit_kanker_value`,
    t.`sakit_hemofilia_label`,
    t.`sakit_hemofilia_value`,
    t.`sakit_ginjal_label`,
    t.`sakit_ginjal_value`,
    t.`sakit_hiv_label`,
    t.`sakit_hiv_value`,
    t.`sakit_kolestrol_label`
FROM tgr_fd68e454.nested_dtsen_var t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
