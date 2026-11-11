-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 08/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`gaji`,
    t.`biaya_produksi`,
    t.`biaya_pembelian`,
    t.`operasional`,
    t.`non_operasional`,
    t.`total_pengeluaran`,
    t.`cek_output26f_pml_label`,
    t.`cek_output26f_pml_value`,
    t.`nilai_pendapatan`,
    t.`pendapatan_lain`,
    t.`total_pendapatan`,
    t.`cek_input27c_pml_label`,
    t.`cek_input27c_pml_value`,
    t.`pendapatan_online`,
    t.`aset_usaha_thn`,
    t.`aset_lain_thn`,
    t.`total_aset_thn`,
    t.`rentang_aset_thn_label`,
    t.`rentang_aset_thn_value`,
    t.`luas_tanah_thn`,
    t.`cek_asetThn_pml_label`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
