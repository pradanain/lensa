-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 03/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`no_kk`,
    t.`nik`,
    t.`nama_kk`,
    t.`htmlHasilPemadananNIK_p`,
    t.`nama_ak_lain`,
    t.`alamat_lookup_umkm`,
    t.`jumlah_usaha_prelist`,
    t.`ada_keluarga_label`,
    t.`ada_keluarga_value`,
    t.`ada_bang_usaha_label`,
    t.`ada_bang_usaha_value`,
    t.`alamat_prelist`,
    t.`jalan_domisili`,
    t.`nomor_domisili`,
    t.`domisili_label`,
    t.`domisili_value`,
    t.`no_bangunan_terbesar`,
    t.`no_bang`,
    t.`kode_bang_label`,
    t.`kode_bang_value`,
    t.`geotag_accuracy`,
    t.`geotag_latitude`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
