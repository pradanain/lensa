-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 02/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`kec_baru_label`,
    t.`kec_baru_value`,
    t.`desa_baru_label`,
    t.`desa_baru_value`,
    t.`klas_desa`,
    t.`kode_sls`,
    t.`nama_sls`,
    t.`ubah_sls_label`,
    t.`ubah_sls_value`,
    t.`nama_sls_lap`,
    t.`kodepos`,
    t.`jalan_domisili_cawi`,
    t.`nomor_domisili_cawi`,
    t.`domisili_cawi_label`,
    t.`domisili_cawi_value`,
    t.`jenis_prelist`,
    t.`is_new_label`,
    t.`is_new_value`,
    t.`pilih_umkm_label`,
    t.`pilih_umkm_value`,
    t.`nama_lookup_umkm`,
    t.`nama_usaha_bang`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
