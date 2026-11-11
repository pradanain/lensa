-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 03/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`rentang_aset_label`,
    t.`rentang_aset_value`,
    t.`luas_tanah`,
    t.`cek_aset_pml`,
    t.`milik_sendiri`,
    t.`prov_l_label`,
    t.`prov_l_value`,
    t.`kab_l_label`,
    t.`kab_l_value`,
    t.`total_modal`,
    t.`kec_l_label`,
    t.`kec_l_value`,
    t.`desa_l_label`,
    t.`desa_l_value`,
    t.`nama_usaha`,
    t.`nama_komersial`,
    t.`nama_res`,
    t.`hp_res`,
    t.`rt`,
    t.`email_res`,
    t.`rw`,
    t.`kode_pos`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
