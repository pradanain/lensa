-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 05/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`lap_keuangan_label`,
    t.`lap_keuangan_value`,
    t.`keg_utama`,
    t.`produk_sendiri_label`,
    t.`produk_sendiri_value`,
    t.`layanan_mamin_label`,
    t.`layanan_mamin_value`,
    t.`keg_penjualan_label`,
    t.`keg_penjualan_value`,
    t.`keg_jasa_label`,
    t.`keg_jasa_value`,
    t.`kab_prelist`,
    t.`lokasi_usaha_label`,
    t.`lokasi_usaha_value`,
    t.`kab_l_loaded`,
    t.`input`,
    t.`proses`,
    t.`produk`,
    t.`set_kab_l`,
    t.`kbli_genai_label`,
    t.`kbli_genai_value`,
    t.`kbli_label`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
