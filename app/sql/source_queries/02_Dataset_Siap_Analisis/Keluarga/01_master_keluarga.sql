-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [01_KELUARGA_MASTER_FINAL]
--
-- MASTER KELUARGA SE2026 - KABUPATEN BULUNGAN
--
-- UNIT DATA:
-- 1 baris = 1 assignment keluarga
--
-- KEY UTAMA:
-- assignment_id
-- assignment_date_modified
--
-- CAKUPAN:
-- - Kabupaten Bulungan
-- - Assignment aktif
-- - Hanya assignment yang memiliki jawaban keberadaan keluarga
--
-- CATATAN:
-- - Tidak mengambil PPL / PML
-- - Maksimal 25 kolom
-- - nomor_keluarga tidak digunakan karena tidak konsisten terisi
-- - jumlah_ak digunakan untuk menangkap jumlah anggota
--   pada tahap listing
-- ============================================================

SELECT

    /* ========================================================
       A. IDENTITAS / KEY
       ======================================================== */

    /* 01 */
    r.assignment_id,

    /* 02 */
    r.assignment_date_modified,

    /* 03 */
    a.code_identity,

    /* 04
       0 = Prelist
       1 = Tambahan CAPI
       ======================================================== */
    a.listing AS listing_assignment,


    /* ========================================================
       B. WILAYAH
       ======================================================== */

    /* 05 */
    a.level_3_name AS kecamatan,

    /* 06 */
    a.level_4_name AS desa_kelurahan,

    /* 07
       Prioritas Sub-SLS jika tersedia,
       jika tidak gunakan SLS
       ======================================================== */
    COALESCE(
        NULLIF(a.level_6_full_code, ''),
        a.level_5_full_code
    ) AS kode_sls_subsls,

    /* 08 */
    COALESCE(
        NULLIF(a.level_6_name, ''),
        a.level_5_name
    ) AS sls_subsls,


    /* ========================================================
       C. BANGUNAN & KEBERADAAN KELUARGA
       ======================================================== */

    /* 09 */
    r.no_bang AS nomor_bangunan,

    /* 10
       Jumlah anggota hasil tahap listing
       ======================================================== */
    r.jumlah_ak AS jumlah_anggota_listing,

    /* 11
       Jawaban aktual keberadaan keluarga.
       Jangan menggunakan kode_keberedaan_keluarga karena
       field tersebut berisi daftar pilihan/option.
       ======================================================== */
    r.ada_keluarga_value AS kode_keberadaan_keluarga,

    /* 12 */
    r.ada_keluarga_label AS keberadaan_keluarga,


    /* ========================================================
       D. IDENTITAS KELUARGA
       ======================================================== */

    /* 13
       Prioritas:
       1. Nomor KK hasil pendataan
       2. Nomor KK listing
       3. Nomor KK prelist
       ======================================================== */
    COALESCE(
        NULLIF(TRIM(r.dtsen_no_kk), ''),
        NULLIF(TRIM(r.no_kk), ''),
        NULLIF(TRIM(r.no_kk_prelist), '')
    ) AS no_kk,

    /* 14 */
    COALESCE(
        NULLIF(TRIM(r.nik_kk), ''),
        NULLIF(TRIM(r.nik), ''),
        NULLIF(TRIM(r.nik_prelist), '')
    ) AS nik_kk,

    /* 15
       Tidak menggunakan nama_principal sebagai fallback
       agar nama BKU/usaha tidak terbaca sebagai nama KK.
       ======================================================== */
    COALESCE(
        NULLIF(TRIM(r.dtsen_nama_kk), ''),
        NULLIF(TRIM(r.nama_kk), '')
    ) AS nama_kk,

    /* 16 */
    COALESCE(
        NULLIF(TRIM(r.alamat_klrg), ''),
        NULLIF(TRIM(r.jalan_domisili), ''),
        NULLIF(TRIM(r.alamat_prelist), '')
    ) AS alamat_keluarga,


    /* ========================================================
       E. STRUKTUR KELUARGA
       ======================================================== */

    /* 17
       Jumlah anggota sesuai KK
       ======================================================== */
    r.jml_kk AS jumlah_anggota_sesuai_kk,

    /* 18
       Jumlah anggota sesuai hasil pendataan akhir
       ======================================================== */
    r.jml_kk_update AS jumlah_anggota_hasil_pendataan,

    /* 19
       Jumlah keluarga yang tinggal dalam rumah/bangunan
       sesuai rincian kuesioner
       ======================================================== */
    r.jml_ak_tinggal AS jumlah_keluarga_dalam_rumah,


    /* ========================================================
       F. USAHA KELUARGA
       ======================================================== */

    /* 20 */
    r.jumlah_usaha_prelist,

    /* 21 */
    r.jumlah_usaha_ditemukan,


    /* ========================================================
       G. PENGGUNAAN BANGUNAN
       ======================================================== */

    /* 22 */
    r.kode_bang_value AS kode_penggunaan_bangunan,


    /* ========================================================
       H. GEOTAG
       ======================================================== */

    /* 23 */
    r.geotag_accuracy,

    /* 24 */
    r.geotag_latitude,

    /* 25 */
    r.geotag_longitude


FROM tgr_fd68e454.root_table r

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON r.assignment_id = a.assignment_id


WHERE
    /* ========================================================
       KABUPATEN BULUNGAN
       ======================================================== */
    a.level_2_full_code = '6502'

    /* ========================================================
       GOLDEN RULE:
       hanya assignment induk yang masih aktif
       ======================================================== */
    AND a.is_active = 1

    /* ========================================================
       FILTER KELUARGA

       ada_keluarga_value adalah jawaban aktual keberadaan
       keluarga, sekaligus membedakan assignment keluarga
       dengan BKU/usaha.
       ======================================================== */
    AND r.ada_keluarga_value IS NOT NULL


ORDER BY
    a.level_3_full_code,
    a.level_4_full_code,
    kode_sls_subsls,
    r.no_bang,
    r.assignment_id;
