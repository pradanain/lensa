-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 10/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`is_cawi`,
    t.`tanggal_anomali`,
    t.`is_from_cawi`,
    t.`anomali_8_resolved_at`,
    t.`is_cawi_keluarga`,
    t.`tanda_info`,
    t.`anomali_7_resolved_at`,
    t.`ket_editable`,
    t.`anomali_6_resolved_at`,
    t.`ub_prelist`,
    t.`kode_prov`,
    t.`prelist_dtsen_var`,
    t.`anomali_5_resolved_at`,
    t.`prov_kab`,
    t.`anomali_4_resolved_at`,
    t.`jk_krt`,
    t.`ub`,
    t.`anomali_3_resolved_at`,
    t.`umur_krt`,
    t.`flag_pbi`,
    t.`anomali_2_resolved_at`,
    t.`anomali_1_resolved_at`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
