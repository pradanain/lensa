-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 05/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`perkebunan_label`,
    t.`perkebunan_value`,
    t.`peternakan_label`,
    t.`peternakan_value`,
    t.`kehutanan_label`,
    t.`kehutanan_value`,
    t.`perikanan_label`,
    t.`perikanan_value`,
    t.`jasa_pertanian_label`,
    t.`jasa_pertanian_value`,
    t.`jumlah_usaha_ditemukan`,
    t.`dtsen_nama_kk`,
    t.`dtsen_no_kk`,
    t.`jml_kk`,
    t.`jml_kk_update`,
    t.`jns_bangunan_label`,
    t.`jns_bangunan_value`,
    t.`jns_bangunan_lain`,
    t.`nm_apt`,
    t.`jml_ak_tinggal`,
    t.`status_kepemilikan_label`,
    t.`status_kepemilikan_value`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
