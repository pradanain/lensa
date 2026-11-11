-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 09/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`anomali_3_penjelasan`,
    t.`anomali_4_penjelasan`,
    t.`anomali_5_penjelasan`,
    t.`anomali_6_penjelasan`,
    t.`anomali_7_penjelasan`,
    t.`anomali_8_penjelasan`,
    t.`anomali_1_dtsen_penjelasan`,
    t.`anomali_2_dtsen_penjelasan`,
    t.`anomali_3_dtsen_penjelasan`,
    t.`anomali_4_dtsen_penjelasan`,
    t.`anomali_5_dtsen_penjelasan`,
    t.`anomali_6_dtsen_penjelasan`,
    t.`anomali_7_dtsen_penjelasan`,
    t.`tanggal_mulai_anomali`,
    t.`nama_info`,
    t.`nik_kk`,
    t.`label_usaha`,
    t.`cek_anomali`,
    t.`prelist_dtsen`,
    t.`idsbr_keluarga`,
    t.`idsbr_match`,
    t.`cawi_identifier`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
