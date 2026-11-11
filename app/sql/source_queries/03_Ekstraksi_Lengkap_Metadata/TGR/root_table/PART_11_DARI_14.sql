-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 11/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`no_kk_prelist`,
    t.`nik_prelist`,
    t.`mode`,
    t.`nama_principal`,
    t.`var_desa`,
    t.`anomali_1_dtsen_resolved_at`,
    t.`has_kodepos`,
    t.`anomali_2_dtsen_resolved_at`,
    t.`hasilPemadananNIK_p`,
    t.`htmlHasilPemadananNIK2_p`,
    t.`anomali_3_dtsen_resolved_at`,
    t.`anomali_4_dtsen_resolved_at`,
    t.`anomali_5_dtsen_resolved_at`,
    t.`anomali_6_dtsen_resolved_at`,
    t.`jml_meteran_var`,
    t.`anomali_7_dtsen_resolved_at`,
    t.`alamat_klrg`,
    t.`total_pendapatan_keluarga_sebulan`,
    t.`kode_keberedaan_keluarga`,
    t.`total_pengeluaran_keluarga_sebulan`,
    t.`kode_keluarga_new`,
    t.`kode_bangunan_new`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
