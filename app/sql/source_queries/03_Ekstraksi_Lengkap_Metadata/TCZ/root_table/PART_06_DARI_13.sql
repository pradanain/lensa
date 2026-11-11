-- ======================================================================
-- RAW tcz_37526b20.root_table - BAGIAN 06/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`kbli_value`,
    t.`kode_kab`,
    t.`kategori`,
    t.`kode_kab_full`,
    t.`cek_kbli_pml`,
    t.`klasifikasi_label`,
    t.`klasifikasi_value`,
    t.`kec_l_loaded`,
    t.`jaringan_label`,
    t.`jaringan_value`,
    t.`set_kec_l`,
    t.`kode_kec_full`,
    t.`desakel`,
    t.`nama_kp`,
    t.`alamat_kp`,
    t.`desa_l_loaded`,
    t.`email_kp`,
    t.`negara_kp_label`,
    t.`negara_kp_value`,
    t.`set_desa_l`,
    t.`prov_kp_label`,
    t.`prov_kp_value`
FROM tcz_37526b20.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
