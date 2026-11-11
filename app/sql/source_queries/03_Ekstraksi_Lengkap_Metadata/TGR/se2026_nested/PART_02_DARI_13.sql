-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 02/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`eks`,
    t.`email`,
    t.`hp`,
    t.`website`,
    t.`jenis_kawasan_label`,
    t.`jenis_kawasan_value`,
    t.`nama_kek_ki_label`,
    t.`nama_kek_ki_value`,
    t.`nama_kawasan`,
    t.`jenis_usaha_label`,
    t.`jenis_usaha_value`,
    t.`alamat_usaha_utama`,
    t.`prov_usaha_utama_label`,
    t.`prov_usaha_utama_value`,
    t.`kab_usaha_utama_label`,
    t.`kab_usaha_utama_value`,
    t.`punya_nib_label`,
    t.`punya_nib_value`,
    t.`nib`,
    t.`tidak_nib_label`,
    t.`tidak_nib_value`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
