-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 03/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`nib_lainnya`,
    t.`badan_usaha_label`,
    t.`badan_usaha_value`,
    t.`koperasi_kdkmp_label`,
    t.`koperasi_kdkmp_value`,
    t.`jenis_koperasi_label`,
    t.`jenis_koperasi_value`,
    t.`lap_keuangan_label`,
    t.`lap_keuangan_value`,
    t.`pengusaha_var_label`,
    t.`pengusaha_var_value`,
    t.`pengusaha`,
    t.`jk_var`,
    t.`jk_label`,
    t.`jk_value`,
    t.`umur_pj_var`,
    t.`umur`,
    t.`nik_pengusaha_var`,
    t.`nik_pengusaha`,
    t.`keg_utama`,
    t.`produk_sendiri_label`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
