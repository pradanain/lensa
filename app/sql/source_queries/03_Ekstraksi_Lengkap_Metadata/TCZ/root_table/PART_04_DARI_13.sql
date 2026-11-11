-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 04/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`tgl_res`,
    t.`kode_area`,
    t.`ttd_res`,
    t.`no_telp`,
    t.`eks`,
    t.`email`,
    t.`hp`,
    t.`website`,
    t.`jenis_kawasan_label`,
    t.`jenis_kawasan_value`,
    t.`nama_kek_ki_label`,
    t.`nama_kek_ki_value`,
    t.`nama_kawasan`,
    t.`punya_nib_label`,
    t.`punya_nib_value`,
    t.`nib`,
    t.`badan_usaha_label`,
    t.`badan_usaha_value`,
    t.`koperasi_kdkmp_label`,
    t.`koperasi_kdkmp_value`,
    t.`jenis_koperasi_label`,
    t.`jenis_koperasi_value`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
