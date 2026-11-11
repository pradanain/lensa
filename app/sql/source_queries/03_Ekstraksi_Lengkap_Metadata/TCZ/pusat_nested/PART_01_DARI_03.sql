-- ======================================================================
-- RAW tcz_37526b20.pusat_nested - BAGIAN 01/03
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`kp_jenis_label`,
    t.`kp_jenis_value`,
    t.`kp_prov_label`,
    t.`kp_prov_value`,
    t.`kp_kab_label`,
    t.`kp_kab_value`,
    t.`kp_tk`,
    t.`kp_kbli_label`,
    t.`kp_kbli_value`,
    t.`kp_cabang`,
    t.`kp_cat`,
    t.`kp_pengeluaran`,
    t.`kp_pendapatan`,
    t.`kp_total_aset`,
    t.`kp_var`,
    t.`kode_jenis`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`assignment_listing`,
    t.`assignment_status_alias`,
    t.`assignment_status_id`
FROM tcz_37526b20.pusat_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
