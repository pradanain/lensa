-- ======================================================================
-- RAW tgr_fd68e454.nested_dtsen_var - BAGIAN 01/06
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`no_urut_kk_var`,
    t.`nama_dtsen_var`,
    t.`sekolah_label`,
    t.`sekolah_value`,
    t.`ijazah_label`,
    t.`ijazah_value`,
    t.`profesi_label`,
    t.`profesi_value`,
    t.`profesi_lainnya`,
    t.`status_kerja_label`,
    t.`status_kerja_value`,
    t.`pendapatan_pekerjaan_label`,
    t.`pendapatan_pekerjaan_value`,
    t.`pend_gaji`,
    t.`pend_tunjangan`,
    t.`pend_uangmkn`,
    t.`pend_honor`,
    t.`pend_lembur`,
    t.`pend_lainnya`,
    t.`nilai_pend_pekerjaan`,
    t.`pendapatan_usaha_label`
FROM tgr_fd68e454.nested_dtsen_var t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
