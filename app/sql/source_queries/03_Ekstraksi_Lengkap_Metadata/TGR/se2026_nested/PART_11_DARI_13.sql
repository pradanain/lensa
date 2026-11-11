-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 11/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`idsbr`,
    t.`alamat_usaha_var`,
    t.`alamat_usaha`,
    t.`hasilCekNIB`,
    t.`pengusaha_var_prelist`,
    t.`hasilPemadananNIK_l`,
    t.`jenis_kegiatan`,
    t.`kbli_prelist`,
    t.`kbli_genai_cawi`,
    t.`kbli_cawi`,
    t.`kbli_akhir`,
    t.`kategori_2025`,
    t.`msg_error_kategori`,
    t.`total_tk_jk_var`,
    t.`total_tk_bayar_var`,
    t.`total_pengeluaran_var`,
    t.`total_pendapatan_var`,
    t.`total_aset_thn_var`,
    t.`info_total_var`,
    t.`total_pengeluaran_bln_var`,
    t.`total_pendapatan_bln_var`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
