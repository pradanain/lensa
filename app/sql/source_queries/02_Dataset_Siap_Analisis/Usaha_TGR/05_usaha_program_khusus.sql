-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [05_USAHA_PROGRAM_KHUSUS]
--
-- UNIT:
-- 1 baris = 1 usaha Ditemukan / Baru
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
-- + index1
--
-- JUMLAH KOLOM: 25
-- ============================================================

SELECT

    /* ========================================================
       A. KEY
       ======================================================== */

    /* 01 */
    u.assignment_id,

    /* 02 */
    u.assignment_date_modified,

    /* 03 */
    u.index1,


    /* ========================================================
       B. LINGKUNGAN & EKONOMI KREATIF
       ======================================================== */

    /* 04 */
    u.produksi_lingkungan_value
        AS memproduksi_produk_ramah_lingkungan,

    /* 05 */
    u.perlindungan_lingkungan_value
        AS menggunakan_input_perlindungan_lingkungan,

    /* 06 */
    u.produk_seni_value
        AS menggunakan_produk_seni_budaya_teknologi,


    /* ========================================================
       C. HALAL
       ======================================================== */

    /* 07 */
    u.halal_value
        AS mempunyai_produk_bersertifikat_halal,

    /* 08 */
    u.sudah_halal
        AS jumlah_varian_sudah_halal,

    /* 09 */
    u.belum_halal
        AS jumlah_varian_belum_halal,


    /* ========================================================
       D. IZIN EDAR / BPOM
       ======================================================== */

    /* 10 */
    u.izin_edar_value
        AS mempunyai_izin_edar,

    /* 11 */
    u.sudah_bpom
        AS jumlah_varian_sudah_bpom,

    /* 12 */
    u.belum_bpom
        AS jumlah_varian_belum_bpom,


    /* ========================================================
       E. PROGRAM PEMERINTAH
       ======================================================== */

    /* 13 */
    u.mitra_kdkmp_value
        AS bermitra_kdkmp,

    /* 14 */
    u.peran_mbg_value
        AS terlibat_program_mbg,


    /* ========================================================
       F. TRANSAKSI DENGAN NONPENDUDUK
       ======================================================== */

    /* 15 */
    u.barang_non_pddk_value
        AS transaksi_barang_nonpenduduk,

    /* 16 */
    u.jasa_non_pddk_value
        AS penjualan_jasa_nonpenduduk,

    /* 17 */
    u.beli_jasa_non_pddk_value
        AS pembelian_jasa_nonpenduduk,


    /* ========================================================
       G. TENAGA KERJA
       ======================================================== */

    /* 18 */
    u.tk_laki
        AS pekerja_laki_laki,

    /* 19 */
    u.tk_pr
        AS pekerja_perempuan,

    /* 20 */
    u.total_tk_jk
        AS total_pekerja_jenis_kelamin,

    /* 21 */
    u.tk_dibayar
        AS pekerja_dibayar,

    /* 22 */
    u.tk_tdk_dibayar
        AS pekerja_tidak_dibayar,

    /* 23 */
    u.total_tk_bayar
        AS total_pekerja_status_bayar,


    /* ========================================================
       H. TAHUN OPERASI
       ======================================================== */

    /* 24 */
    u.tahun_operasi
        AS tahun_mulai_operasi,


    /* ========================================================
       I. AUDIT KONSISTENSI TENAGA KERJA
       ======================================================== */

    /* 25 */
    CASE

        WHEN u.tk_laki IS NULL
         AND u.tk_pr IS NULL
         AND u.total_tk_jk IS NULL
         AND u.tk_dibayar IS NULL
         AND u.tk_tdk_dibayar IS NULL
         AND u.total_tk_bayar IS NULL
            THEN 'TIDAK_DIISI'

        WHEN u.tk_laki IS NOT NULL
         AND u.tk_pr IS NOT NULL
         AND u.total_tk_jk IS NOT NULL
         AND (u.tk_laki + u.tk_pr) <> u.total_tk_jk
            THEN 'JK_TIDAK_SESUAI'

        WHEN u.tk_dibayar IS NOT NULL
         AND u.tk_tdk_dibayar IS NOT NULL
         AND u.total_tk_bayar IS NOT NULL
         AND (u.tk_dibayar + u.tk_tdk_dibayar) <> u.total_tk_bayar
            THEN 'BAYAR_TIDAK_SESUAI'

        WHEN u.tk_laki IS NOT NULL
         AND u.tk_pr IS NOT NULL
         AND u.total_tk_jk IS NOT NULL
         AND u.tk_dibayar IS NOT NULL
         AND u.tk_tdk_dibayar IS NOT NULL
         AND u.total_tk_bayar IS NOT NULL
            THEN 'SESUAI'

        ELSE 'BELUM_LENGKAP'

    END AS status_konsistensi_pekerja


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
