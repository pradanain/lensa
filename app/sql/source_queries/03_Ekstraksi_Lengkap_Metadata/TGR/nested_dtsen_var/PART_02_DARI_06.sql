-- ======================================================================
-- RAW tgr_fd68e454.nested_dtsen_var - BAGIAN 02/06
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`pendapatan_usaha_value`,
    t.`pend_usaha`,
    t.`pend_usaha_lain_label`,
    t.`pend_usaha_lain_value`,
    t.`nilai_pend_lain`,
    t.`rekening_label`,
    t.`rekening_value`,
    t.`dis_fisik_label`,
    t.`dis_fisik_value`,
    t.`dis_mental_label`,
    t.`dis_mental_value`,
    t.`dis_intelek_label`,
    t.`dis_intelek_value`,
    t.`dis_netra_label`,
    t.`dis_netra_value`,
    t.`dis_rungu_label`,
    t.`dis_rungu_value`,
    t.`dis_wicara_label`,
    t.`dis_wicara_value`,
    t.`sakit_hipertensi_label`,
    t.`sakit_hipertensi_value`
FROM tgr_fd68e454.nested_dtsen_var t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
