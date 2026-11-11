-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 08/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`nilai_mobil`,
    t.`jumlah_lahan_new`,
    t.`nilai_lahan`,
    t.`jumlah_rumah_new`,
    t.`nilai_rumah`,
    t.`foto_depan_filename`,
    t.`foto_depan_uri`,
    t.`foto_depan_url`,
    t.`foto_ruang_tamu_filename`,
    t.`foto_ruang_tamu_uri`,
    t.`foto_ruang_tamu_url`,
    t.`nama_info_list_value`,
    t.`nama_lain`,
    t.`telp_info`,
    t.`email_info`,
    t.`catatan`,
    t.`waktu_selesai`,
    t.`cek_anomali_button`,
    t.`anomali_admin`,
    t.`catatan_anomali_admin`,
    t.`anomali_1_penjelasan`,
    t.`anomali_2_penjelasan`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
