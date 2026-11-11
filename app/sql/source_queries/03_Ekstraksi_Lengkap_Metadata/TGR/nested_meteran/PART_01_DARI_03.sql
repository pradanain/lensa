-- ======================================================================
-- RAW tgr_fd68e454.nested_meteran - BAGIAN 01/03
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`urutan_meteran_lain`,
    t.`daya_terpasang_label`,
    t.`daya_terpasang_value`,
    t.`id_pln_pilih_label`,
    t.`id_pln_pilih_value`,
    t.`id_pelanggan`,
    t.`no_meteran`,
    t.`hasilCekIdPel`,
    t.`hasilCekMeteran`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`assignment_listing`,
    t.`assignment_status_alias`,
    t.`assignment_status_id`,
    t.`cek_idpel`,
    t.`is_active`,
    t.`level_1_code`,
    t.`level_1_name`,
    t.`level_10_code`,
    t.`level_10_full_code`,
    t.`level_10_name`
FROM tgr_fd68e454.nested_meteran t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
