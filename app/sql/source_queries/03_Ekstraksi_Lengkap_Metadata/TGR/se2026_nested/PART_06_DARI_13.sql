-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 06/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`internet_beli_value`,
    t.`internet_promosi_label`,
    t.`internet_promosi_value`,
    t.`internet_lainnya_label`,
    t.`internet_lainnya_value`,
    t.`digital_label`,
    t.`digital_value`,
    t.`produksi_lingkungan_label`,
    t.`produksi_lingkungan_value`,
    t.`perlindungan_lingkungan_label`,
    t.`perlindungan_lingkungan_value`,
    t.`produk_seni_label`,
    t.`produk_seni_value`,
    t.`halal_label`,
    t.`halal_value`,
    t.`sudah_halal`,
    t.`belum_halal`,
    t.`izin_edar_label`,
    t.`izin_edar_value`,
    t.`sudah_bpom`,
    t.`belum_bpom`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
