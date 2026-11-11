-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 01/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`kunjungan_1`,
    t.`catatan_1`,
    t.`kunjungan_2`,
    t.`catatan_2`,
    t.`kunjungan_3`,
    t.`alasan_nr_label`,
    t.`alasan_nr_value`,
    t.`catatan_3`,
    t.`keberadaan_label`,
    t.`keberadaan_value`,
    t.`kunjungan_pml`,
    t.`geotag_pml_accuracy`,
    t.`geotag_pml_latitude`,
    t.`geotag_pml_longitude`,
    t.`catatan_pml`,
    t.`prov`,
    t.`kab`,
    t.`kec`,
    t.`desa_baru`,
    t.`alasan_nib_label`,
    t.`alasan_nib_value`,
    t.`tulis_alasan_nib`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
