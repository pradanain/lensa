-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 06/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`status_kepemilikan_lain`,
    t.`bukti_kepemilikan_label`,
    t.`bukti_kepemilikan_value`,
    t.`sewa_sendiri`,
    t.`sewa_kontrak`,
    t.`sewa_dinas`,
    t.`luas_lantai`,
    t.`jns_lantai_label`,
    t.`jns_lantai_value`,
    t.`kondisi_lantai_label`,
    t.`kondisi_lantai_value`,
    t.`jns_dinding_label`,
    t.`jns_dinding_value`,
    t.`kondisi_dinding_label`,
    t.`kondisi_dinding_value`,
    t.`jns_atap_label`,
    t.`jns_atap_value`,
    t.`kondisi_atap_label`,
    t.`kondisi_atap_value`,
    t.`tempat_bab_label`,
    t.`tempat_bab_value`,
    t.`jns_closet_label`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
