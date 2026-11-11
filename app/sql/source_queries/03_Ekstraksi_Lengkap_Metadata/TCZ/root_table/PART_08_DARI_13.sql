-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 08/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`digital_label`,
    t.`digital_value`,
    t.`produksi_lingkungan_label`,
    t.`produksi_lingkungan_value`,
    t.`perlindungan_lingkungan_label`,
    t.`perlindungan_lingkungan_value`,
    t.`kbli_2025`,
    t.`produk_seni_label`,
    t.`produk_seni_value`,
    t.`sudah_halal`,
    t.`belum_halal`,
    t.`izin_edar_label`,
    t.`izin_edar_value`,
    t.`list_kbli_mbg`,
    t.`sudah_bpom`,
    t.`belum_bpom`,
    t.`list_kbli_sekolah`,
    t.`mitra_kdkmp_label`,
    t.`mitra_kdkmp_value`,
    t.`peran_mbg_label`,
    t.`peran_mbg_value`,
    t.`var_b1r9b`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
