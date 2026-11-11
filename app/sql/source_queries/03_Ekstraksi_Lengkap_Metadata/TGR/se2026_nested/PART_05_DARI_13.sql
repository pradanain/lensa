-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 05/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`jaringan_label`,
    t.`jaringan_value`,
    t.`jumlah_kc`,
    t.`nama_kp`,
    t.`alamat_kp`,
    t.`email_kp`,
    t.`negara_kp_label`,
    t.`negara_kp_value`,
    t.`prov_kp_label`,
    t.`prov_kp_value`,
    t.`kab_kp_label`,
    t.`kab_kp_value`,
    t.`internet_label`,
    t.`internet_value`,
    t.`internet_produksi_label`,
    t.`internet_produksi_value`,
    t.`internet_pesanan_label`,
    t.`internet_pesanan_value`,
    t.`internet_distribusi_label`,
    t.`internet_distribusi_value`,
    t.`internet_beli_label`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
