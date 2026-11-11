-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 12/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`jumlah_tabung3kg`,
    t.`jumlah_tabung5kg`,
    t.`no_keluarga_terbesar`,
    t.`no_keluarga`,
    t.`jumlah_kulkas`,
    t.`jumlah_ac`,
    t.`jumlah_emas`,
    t.`pilihan_kode_bang`,
    t.`jumlah_laptop`,
    t.`jumlah_motor`,
    t.`jumlah_mobil`,
    t.`jumlah_lahan`,
    t.`jumlah_rumah`,
    t.`usaha_gabung`,
    t.`nama_usaha_prelist`,
    t.`idsbr_all`,
    t.`email_all`,
    t.`skala_usaha_all`,
    t.`idunik_MSSD`,
    t.`jumlah_usaha`,
    t.`ya_pertanian`,
    t.`ya_nonpertanian`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
