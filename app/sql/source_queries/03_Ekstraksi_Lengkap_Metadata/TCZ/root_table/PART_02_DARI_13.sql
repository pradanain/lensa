-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 02/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`jenis_prelist`,
    t.`nama_pj`,
    t.`jk_pj_label`,
    t.`jk_pj_value`,
    t.`umur_pj`,
    t.`nik_pj`,
    t.`jml_kc`,
    t.`sertifikat_halal_label`,
    t.`sertifikat_halal_value`,
    t.`non_pddk_barang_label`,
    t.`non_pddk_barang_value`,
    t.`non_pddk_jasa_label`,
    t.`non_pddk_jasa_value`,
    t.`tk_perempuan`,
    t.`tk_total`,
    t.`cek_tk_pml`,
    t.`cek_output_pml`,
    t.`persen_online`,
    t.`cek_input_pml`,
    t.`aset_tanah`,
    t.`aset_non_tanah`,
    t.`aset_total`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
