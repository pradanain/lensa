-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 07/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`jns_closet_value`,
    t.`buang_tinja_label`,
    t.`buang_tinja_value`,
    t.`air_minum_label`,
    t.`air_minum_value`,
    t.`sumber_penerangan_label`,
    t.`sumber_penerangan_value`,
    t.`jml_meteran`,
    t.`listrik_sebulan`,
    t.`pulsa_sebulan`,
    t.`pengeluaran_makanan_mingguan`,
    t.`pengeluaran_non_makan_bulanan`,
    t.`pengeluaran_non_makan_tahunan`,
    t.`jumlah_tabung3kg_new`,
    t.`jumlah_tabung5kg_new`,
    t.`jumlah_kulkas_new`,
    t.`jumlah_ac_new`,
    t.`jumlah_emas_new`,
    t.`jumlah_laptop_new`,
    t.`jumlah_motor_new`,
    t.`nilai_motor`,
    t.`jumlah_mobil_new`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
