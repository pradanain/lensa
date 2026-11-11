-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 09/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`cek_asetThn_pml_value`,
    t.`pribadi`,
    t.`non_profit`,
    t.`publik`,
    t.`non_publik`,
    t.`pemerintah`,
    t.`asing`,
    t.`info_total`,
    t.`gaji_bln`,
    t.`biaya_produksi_bln`,
    t.`biaya_pembelian_bln`,
    t.`operasional_bln`,
    t.`non_operasional_bln`,
    t.`cek_output30f_pml_label`,
    t.`cek_output30f_pml_value`,
    t.`total_pengeluaran_bln`,
    t.`nilai_pendapatan_bln`,
    t.`pendapatan_lain_bln`,
    t.`total_pendapatan_bln`,
    t.`cek_input31c_pml_label`,
    t.`cek_input31c_pml_value`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
