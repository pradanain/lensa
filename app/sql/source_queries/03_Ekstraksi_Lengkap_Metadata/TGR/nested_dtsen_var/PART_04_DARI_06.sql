-- ======================================================================
-- RAW tgr_fd68e454.nested_dtsen_var - BAGIAN 04/06
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`sakit_kolestrol_value`,
    t.`sakit_sirosis_label`,
    t.`sakit_sirosis_value`,
    t.`sakit_talasemia_label`,
    t.`sakit_talasemia_value`,
    t.`sakit_leukemia_label`,
    t.`sakit_leukemia_value`,
    t.`sakit_alzheimer_label`,
    t.`sakit_alzheimer_value`,
    t.`sakit_lainnya_label`,
    t.`sakit_lainnya_value`,
    t.`ec_art_dtsen`,
    t.`ec_art_pendapatan`,
    t.`set_sekolah_prelist`,
    t.`sekolah_prelist`,
    t.`set_ijazah_prelist`,
    t.`ijazah_prelist`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`assignment_listing`,
    t.`assignment_status_alias`
FROM tgr_fd68e454.nested_dtsen_var t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
