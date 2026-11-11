-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [06_USAHA_EKONOMI_TAHUNAN]
--
-- EKONOMI USAHA TAHUN 2025
--
-- UNIT:
-- 1 baris = 1 usaha Ditemukan/Baru
--           yang mulai beroperasi sebelum 2026
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
-- + index1
--
-- JUMLAH KOLOM: 23
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
       B. TAHUN OPERASI
       ======================================================== */

    /* 04 */
    u.tahun_operasi
        AS tahun_mulai_operasi,


    /* ========================================================
       C. PENGELUARAN TAHUN 2025
       ======================================================== */

    /* 05 */
    u.gaji
        AS pengeluaran_gaji_jaminan_sosial,

    /* 06 */
    u.biaya_produksi
        AS biaya_produksi,

    /* 07 */
    u.biaya_pembelian
        AS biaya_pembelian_barang_terjual,

    /* 08 */
    u.operasional
        AS biaya_operasional,

    /* 09 */
    u.non_operasional
        AS biaya_non_operasional,

    /* 10 */
    u.total_pengeluaran
        AS total_pengeluaran_2025,


    /* ========================================================
       D. PENDAPATAN TAHUN 2025
       ======================================================== */

    /* 11 */
    u.nilai_pendapatan
        AS pendapatan_utama_2025,

    /* 12 */
    u.pendapatan_lain
        AS pendapatan_lainnya_2025,

    /* 13 */
    u.total_pendapatan
        AS total_pendapatan_2025,

    /* 14 */
    u.pendapatan_online
        AS persen_pendapatan_online,


    /* ========================================================
       E. ASET 31 DESEMBER 2025
       ======================================================== */

    /* 15 */
    u.aset_usaha_thn
        AS aset_tanah_bangunan_2025,

    /* 16 */
    u.aset_lain_thn
        AS aset_selain_tanah_bangunan_2025,

    /* 17 */
    u.total_aset_thn
        AS total_aset_2025,

    /* 18 */
    u.rentang_aset_thn_value
        AS kode_rentang_aset_2025,

    /* 19 */
    u.rentang_aset_thn_label
        AS rentang_aset_2025,

    /* 20 */
    u.luas_tanah_thn
        AS luas_tanah_usaha_m2,


    /* ========================================================
       F. AUDIT TOTAL
       ======================================================== */

    /* 21 */
    CASE
        WHEN u.total_pengeluaran IS NULL
            THEN 'TIDAK_DIISI'

        WHEN
              COALESCE(u.gaji, 0)
            + COALESCE(u.biaya_produksi, 0)
            + COALESCE(u.biaya_pembelian, 0)
            + COALESCE(u.operasional, 0)
            + COALESCE(u.non_operasional, 0)
            = u.total_pengeluaran
            THEN 'SESUAI'

        ELSE 'TIDAK_SESUAI'
    END AS status_total_pengeluaran,


    /* 22 */
    CASE
        WHEN u.total_pendapatan IS NULL
            THEN 'TIDAK_DIISI'

        WHEN
              COALESCE(u.nilai_pendapatan, 0)
            + COALESCE(u.pendapatan_lain, 0)
            = u.total_pendapatan
            THEN 'SESUAI'

        ELSE 'TIDAK_SESUAI'
    END AS status_total_pendapatan,


    /* 23 */
    CASE
        WHEN u.total_aset_thn IS NULL
            THEN 'TIDAK_DIISI'

        WHEN
              COALESCE(u.aset_usaha_thn, 0)
            + COALESCE(u.aset_lain_thn, 0)
            = u.total_aset_thn
            THEN 'SESUAI'

        ELSE 'TIDAK_SESUAI'
    END AS status_total_aset


FROM tgr_fd68e454.se2026_nested u

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON u.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'

    AND u.keberadaan_usaha_value IN ('1', '2')

    AND NULLIF(
            TRIM(CAST(u.tahun_operasi AS STRING)),
            ''
        ) IS NOT NULL

    AND CAST(u.tahun_operasi AS INT) < 2026

ORDER BY
    u.assignment_id,
    u.index1;
