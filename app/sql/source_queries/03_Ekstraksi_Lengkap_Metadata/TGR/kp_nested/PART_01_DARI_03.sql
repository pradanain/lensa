-- ======================================================================
-- RAW tgr_fd68e454.kp_nested - BAGIAN 01/03
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1, index2
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`index2`,
    t.`kp_unit`,
    t.`kp_jenis_label`,
    t.`kp_jenis_value`,
    t.`kp_prov_label`,
    t.`kp_prov_value`,
    t.`kp_kab_label`,
    t.`kp_kab_value`,
    t.`kp_produksi_lingkungan_label`,
    t.`kp_produksi_lingkungan_value`,
    t.`kp_perlindungan_lingkungan_label`,
    t.`kp_perlindungan_lingkungan_value`,
    t.`kp_tk`,
    t.`kp_total_pengeluaran`,
    t.`kp_total_pendapatan`,
    t.`kp_total_aset`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`assignment_listing`,
    t.`assignment_status_alias`,
    t.`assignment_status_id`
FROM tgr_fd68e454.kp_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`, t.`index2`;
