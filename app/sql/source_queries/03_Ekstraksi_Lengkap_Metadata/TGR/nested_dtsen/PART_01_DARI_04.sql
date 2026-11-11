-- ======================================================================
-- RAW tgr_fd68e454.nested_dtsen - BAGIAN 01/04
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`nama_dtsen`,
    t.`nik_dtsen`,
    t.`hubungan_label`,
    t.`hubungan_value`,
    t.`keberadaan_dtsen_label`,
    t.`keberadaan_dtsen_value`,
    t.`alamat_dn_label`,
    t.`alamat_dn_value`,
    t.`prov_dn_label`,
    t.`prov_dn_value`,
    t.`kab_dn_label`,
    t.`kab_dn_value`,
    t.`domisili_ln_label`,
    t.`domisili_ln_value`,
    t.`status_kawin_label`,
    t.`status_kawin_value`,
    t.`jk_dtsen_label`,
    t.`jk_dtsen_value`,
    t.`tgl_lahir`,
    t.`bln_lahir_label`,
    t.`bln_lahir_value`
FROM tgr_fd68e454.nested_dtsen t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
