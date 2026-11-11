-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 13/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`total_pengeluaran_float`,
    t.`total_modal_int`,
    t.`aset_total_nvarchar512`,
    t.`total_modal_nvarchar512`,
    t.`total_pendapatan_nvarchar512`,
    t.`total_pengeluaran_nvarchar512`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
