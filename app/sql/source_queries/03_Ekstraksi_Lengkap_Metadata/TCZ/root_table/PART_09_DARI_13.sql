-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 09/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`beli_jasa_non_pddk_label`,
    t.`beli_jasa_non_pddk_value`,
    t.`narasi`,
    t.`tk_laki`,
    t.`aset_total_var`,
    t.`total_modal_var`,
    t.`b1r9b_ket`,
    t.`tahun_operasi`,
    t.`gaji`,
    t.`biaya_produksi`,
    t.`biaya_pembelian`,
    t.`operasional`,
    t.`non_operasional`,
    t.`total_pengeluaran`,
    t.`nilai_pendapatan`,
    t.`pendapatan_lain`,
    t.`total_pendapatan`,
    t.`non_profit`,
    t.`publik`,
    t.`non_publik`,
    t.`pemerintah`,
    t.`asing`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
