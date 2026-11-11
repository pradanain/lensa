-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 01/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`pilih_umkm_sls_label`,
    t.`pilih_umkm_sls_value`,
    t.`prov_l`,
    t.`kab_l`,
    t.`kec_l`,
    t.`desa_l`,
    t.`kodesls_l`,
    t.`sls_l`,
    t.`no_bang_l`,
    t.`no_usaha`,
    t.`nama_usaha`,
    t.`keberadaan_usaha_label`,
    t.`keberadaan_usaha_value`,
    t.`nama_usaha_edit`,
    t.`nama_komersial`,
    t.`alamat_usaha_view`,
    t.`rt`,
    t.`rw`,
    t.`kode_pos`,
    t.`kode_area`,
    t.`no_telp`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
