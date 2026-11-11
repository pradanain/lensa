-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 07/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`mitra_kdkmp_label`,
    t.`mitra_kdkmp_value`,
    t.`peran_mbg_label`,
    t.`peran_mbg_value`,
    t.`barang_non_pddk_label`,
    t.`barang_non_pddk_value`,
    t.`jasa_non_pddk_label`,
    t.`jasa_non_pddk_value`,
    t.`beli_jasa_non_pddk_label`,
    t.`beli_jasa_non_pddk_value`,
    t.`tk_laki`,
    t.`tk_pr`,
    t.`total_tk_jk`,
    t.`cek_tk_jk_pml_label`,
    t.`cek_tk_jk_pml_value`,
    t.`tk_dibayar`,
    t.`tk_tdk_dibayar`,
    t.`total_tk_bayar`,
    t.`cek_tk_bayar_pml_label`,
    t.`cek_tk_bayar_pml_value`,
    t.`tahun_operasi`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
