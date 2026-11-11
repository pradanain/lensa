-- ======================================================================
-- MASTER BKU - SEMUA STATUS KEBERADAAN, termasuk 7
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- 1 baris per record root BKU/versi; JANGAN disamakan dengan 1 unit usaha.
-- ======================================================================

SELECT
    r.assignment_id,
    r.assignment_date_modified,
    a.code_identity,
    a.listing AS listing_assignment,
    a.level_3_full_code AS kode_kecamatan,
    a.level_3_name AS kecamatan,
    a.level_4_full_code AS kode_desa,
    a.level_4_name AS desa_kelurahan,
    COALESCE(NULLIF(a.level_6_full_code, ''), a.level_5_full_code) AS kode_sls_subsls,
    COALESCE(NULLIF(a.level_6_name, ''), a.level_5_name) AS sls_subsls,
    r.no_bang AS nomor_bangunan,
    r.nama_usaha_bang AS nama_bangunan_usaha,
    r.nama_lookup_umkm AS nama_lookup_prelist,
    r.alamat_prelist,
    r.jalan_domisili,
    r.kode_bang_value AS kode_penggunaan_bangunan,
    r.kode_bang_label AS penggunaan_bangunan,
    r.ada_bang_usaha_value AS kode_keberadaan_bku,
    r.ada_bang_usaha_label AS keberadaan_bku,
    r.ada_keluarga_value AS kode_keberadaan_keluarga,
    r.ada_keluarga_label AS keberadaan_keluarga,
    r.geotag_accuracy,
    r.geotag_latitude,
    r.geotag_longitude,
    a.assignment_status_alias AS status_assignment
FROM tgr_fd68e454.root_table r
INNER JOIN tgr_fd68e454.base_table_assignment a
    ON r.assignment_id = a.assignment_id
   AND a.is_active = 1
WHERE a.level_2_full_code = '6502'
  AND r.ada_bang_usaha_value IS NOT NULL
ORDER BY a.level_3_full_code, a.level_4_full_code,
         kode_sls_subsls, r.no_bang, r.assignment_id;
