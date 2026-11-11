-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 07/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`kode_desa_full`,
    t.`idsls`,
    t.`kab_kp_label`,
    t.`kab_kp_value`,
    t.`internet_label`,
    t.`internet_value`,
    t.`idunik_PMSS`,
    t.`internet_produksi_label`,
    t.`internet_produksi_value`,
    t.`internet_pesanan_label`,
    t.`internet_pesanan_value`,
    t.`wilayah_ngibar`,
    t.`internet_distribusi_label`,
    t.`internet_distribusi_value`,
    t.`tgl_ngibar`,
    t.`email_prelist`,
    t.`internet_beli_label`,
    t.`internet_beli_value`,
    t.`internet_promosi_label`,
    t.`internet_promosi_value`,
    t.`internet_lainnya_label`,
    t.`internet_lainnya_value`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
