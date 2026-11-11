-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [02_USAHA_PJ_LEGALITAS_FINAL]
--
-- UNIT:
-- 1 baris = 1 usaha Ditemukan / Baru
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
-- + index1
--
-- CAKUPAN:
-- Kabupaten Bulungan
-- keberadaan usaha = Ditemukan / Baru
--
-- JUMLAH KOLOM: 25
-- ============================================================

SELECT

    /* 01 */
    u.assignment_id,

    /* 02 */
    u.assignment_date_modified,

    /* 03 */
    u.index1,


    /* ========================================================
       PENANGGUNG JAWAB
       ======================================================== */

    /* 04 */
    COALESCE(
        NULLIF(TRIM(u.pengusaha), ''),
        NULLIF(TRIM(u.pengusaha_var_label), '')
    ) AS nama_pengusaha_pj,


    /* 05
       NORMALISASI JENIS KELAMIN PJ
       1 = Laki-laki
       2 = Perempuan
       ======================================================== */
    CASE
        WHEN TRIM(CAST(u.jk_value AS STRING)) = '1' THEN '1'
        WHEN TRIM(CAST(u.jk_value AS STRING)) = '2' THEN '2'

        WHEN CAST(u.jk_var AS STRING) LIKE '%value=1%' THEN '1'
        WHEN CAST(u.jk_var AS STRING) LIKE '%value=2%' THEN '2'

        WHEN TRIM(CAST(u.jk_var AS STRING)) = '1' THEN '1'
        WHEN TRIM(CAST(u.jk_var AS STRING)) = '2' THEN '2'

        ELSE NULL
    END AS jenis_kelamin_pj,


    /* 06 */
    COALESCE(
        u.umur,
        u.umur_pj_var
    ) AS umur_pj,


    /* 07 */
    COALESCE(
        NULLIF(TRIM(u.nik_pengusaha), ''),
        NULLIF(TRIM(u.nik_pengusaha_var), '')
    ) AS nik_pengusaha_pj,


    /* ========================================================
       KONTAK
       ======================================================== */

    /* 08 */
    NULLIF(TRIM(u.no_telp), '') AS nomor_telepon,

    /* 09 */
    NULLIF(TRIM(u.hp), '') AS nomor_hp_whatsapp,

    /* 10 */
    NULLIF(TRIM(u.email), '') AS email,

    /* 11 */
    NULLIF(TRIM(u.website), '') AS website,


    /* ========================================================
       KAWASAN & LOKASI USAHA UTAMA
       ======================================================== */

    /* 12 */
    u.jenis_kawasan_value AS jenis_kawasan,

    /* 13 */
    u.nama_kek_ki_value AS kode_nama_kek_ki,

    /* 14 */
    NULLIF(TRIM(u.nama_kawasan), '') AS nama_kawasan,

    /* 15 */
    NULLIF(TRIM(u.alamat_usaha_utama), '') AS alamat_usaha_utama,

    /* 16 */
    u.prov_usaha_utama_value AS provinsi_usaha_utama,

    /* 17 */
    u.kab_usaha_utama_value AS kabupaten_usaha_utama,


    /* ========================================================
       NIB
       ======================================================== */

    /* 18 */
    u.punya_nib_value AS punya_nib,

    /* 19 */
    NULLIF(TRIM(u.nib), '') AS nib,

    /* 20 */
    u.tidak_nib_value AS alasan_tidak_punya_nib,

    /* 21 */
    NULLIF(TRIM(u.nib_lainnya), '') AS alasan_nib_lainnya,


    /* ========================================================
       BADAN USAHA / KOPERASI
       ======================================================== */

    /* 22 */
    u.badan_usaha_value AS badan_usaha,

    /* 23 */
    u.koperasi_kdkmp_value AS koperasi_kdkmp,

    /* 24 */
    u.jenis_koperasi_value AS jenis_koperasi,

    /* 25 */
    u.lap_keuangan_value AS mempunyai_laporan_keuangan


FROM tgr_fd68e454.se2026_nested u

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON u.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'
    AND u.keberadaan_usaha_value IN ('1', '2')

ORDER BY
    u.assignment_id,
    u.index1;
