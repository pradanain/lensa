-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 10/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`metod_isi_label`,
    t.`metod_isi_value`,
    t.`file_input`,
    t.`catatan`,
    t.`kode_prov`,
    t.`tahun_survei`,
    t.`mode`,
    t.`skala_usaha`,
    t.`idsbr`,
    t.`alamat_usaha`,
    t.`var_kbli`,
    t.`result_gen_ai`,
    t.`kbli_prelist`,
    t.`kbli_akhir`,
    t.`kategori_2025`,
    t.`msg_error_kategori`,
    t.`ec_halal`,
    t.`ec_bpom`,
    t.`total_pengeluaran_var`,
    t.`total_pendapatan_var`,
    t.`list_kc`,
    t.`list_error_csv_html`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
