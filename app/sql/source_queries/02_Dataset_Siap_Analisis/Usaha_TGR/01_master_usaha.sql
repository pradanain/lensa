-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [01_USAHA_MASTER]
-- Master usaha keluarga / UMKM SE2026 Kabupaten Bulungan
--
-- UNIT:
-- 1 baris = 1 usaha
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
-- + index1
--
-- CATATAN:
-- - keberadaan_usaha_value = jawaban aktual
-- - kode_keberadaan_usaha BUKAN jawaban aktual
-- - wilayah menggunakan hierarchy assignment roster
-- ============================================================

SELECT
    /* 01 */ u.assignment_id,
    /* 02 */ u.assignment_date_modified,
    /* 03 */ u.index1,

    /* 04 */ a.code_identity,

    /* 05 */ u.is_prelist2,

    /* 06 */ u.level_3_name AS kecamatan,
    /* 07 */ u.level_4_name AS desa_kelurahan,

    /* 08 */
    COALESCE(
        NULLIF(u.level_6_full_code, ''),
        u.level_5_full_code
    ) AS kode_sls_subsls,

    /* 09 */
    COALESCE(
        NULLIF(u.level_6_name, ''),
        u.level_5_name
    ) AS sls_subsls,

    /* 10 */ u.no_bang_l AS nomor_bangunan,
    /* 11 */ u.no_usaha AS nomor_usaha,

    /* 12 */
    COALESCE(
        NULLIF(TRIM(u.nama_usaha_edit), ''),
        NULLIF(TRIM(u.nama_usaha), '')
    ) AS nama_usaha,

    /* 13 */ u.nama_komersial,

    /* 14 */
    u.keberadaan_usaha_value AS kode_keberadaan_usaha,

    /* 15 */
    u.keberadaan_usaha_label AS keberadaan_usaha,

    /* 16 */
    COALESCE(
        NULLIF(TRIM(u.alamat_usaha), ''),
        NULLIF(TRIM(u.alamat_usaha_var), ''),
        NULLIF(TRIM(u.alamat_usaha_view), '')
    ) AS alamat_usaha,

    /* 17 */
    u.jenis_usaha_value AS jenis_usaha,

    /* 18 */
    COALESCE(
        NULLIF(TRIM(u.pengusaha), ''),
        NULLIF(TRIM(u.pengusaha_var_label), '')
    ) AS nama_pengusaha_pj,

    /* 19 */ u.keg_utama AS kegiatan_utama,

    /* 20 */ u.produk AS produk_utama,

    /* 21 */
    COALESCE(
        NULLIF(TRIM(u.kbli_akhir), ''),
        NULLIF(TRIM(u.kbli_value), ''),
        NULLIF(TRIM(u.kbli_prelist), '')
    ) AS kbli,

    /* 22 */
    COALESCE(
        NULLIF(TRIM(u.kategori_2025), ''),
        NULLIF(TRIM(u.kategori), '')
    ) AS kategori,

    /* 23 */ u.skala_usaha,

    /* 24 */ r.geotag_latitude,
    /* 25 */ r.geotag_longitude

FROM tgr_fd68e454.se2026_nested u

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON u.assignment_id = a.assignment_id
   AND a.is_active = 1

LEFT JOIN tgr_fd68e454.root_table r
    ON u.assignment_id = r.assignment_id
   AND u.assignment_date_modified = r.assignment_date_modified

WHERE
    a.level_2_full_code = '6502'

    -- Hanya item roster yang benar-benar mempunyai
    -- jawaban keberadaan usaha
    AND u.keberadaan_usaha_value IS NOT NULL

ORDER BY
    u.level_3_full_code,
    u.level_4_full_code,
    kode_sls_subsls,
    u.no_bang_l,
    u.no_usaha,
    u.index1;
