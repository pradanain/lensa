-- ======================================================================
-- RAW tgr_fd68e454.root_table - BAGIAN 04/14
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`geotag_longitude`,
    t.`foto_depan_p_filename`,
    t.`foto_depan_p_uri`,
    t.`foto_depan_p_url`,
    t.`jumlah_ak_kk`,
    t.`jumlah_ak`,
    t.`usaha_kos_label`,
    t.`usaha_kos_value`,
    t.`usaha_keliling_label`,
    t.`usaha_keliling_value`,
    t.`usaha_online_label`,
    t.`usaha_online_value`,
    t.`usaha_bongkar_label`,
    t.`usaha_bongkar_value`,
    t.`usaha_konstruksi_label`,
    t.`usaha_konstruksi_value`,
    t.`usaha_lain_label`,
    t.`usaha_lain_value`,
    t.`tanaman_pangan_label`,
    t.`tanaman_pangan_value`,
    t.`hortikultura_label`,
    t.`hortikultura_value`
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
