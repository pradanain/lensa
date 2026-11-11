-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 10/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`pendapatan_online_bln`,
    t.`aset_tanah_bln`,
    t.`aset_lain_bln`,
    t.`total_aset_bln`,
    t.`rentang_aset_bln_label`,
    t.`rentang_aset_bln_value`,
    t.`luas_tanah_bln`,
    t.`cek_asetBln_pml_label`,
    t.`cek_asetBln_pml_value`,
    t.`pribadi_didirikan`,
    t.`nonprofit_didirikan`,
    t.`publik_didirikan`,
    t.`nonpublik_didirikan`,
    t.`pemerintah_didirikan`,
    t.`asing_didirikan`,
    t.`info_total_didirikan`,
    t.`pilih_umkm_options`,
    t.`kode_keberadaan_usaha`,
    t.`skala_usaha`,
    t.`is_prelist2`,
    t.`id_pmss`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
