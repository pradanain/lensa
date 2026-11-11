-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- DATASET : 07_USAHA_EKONOMI_BULANAN_MODAL
--
-- DESKRIPSI:
-- Dataset kondisi ekonomi usaha yang mulai beroperasi pada
-- tahun 2026.
--
-- Karena usaha baru tahun 2026 belum mempunyai periode usaha
-- penuh selama tahun 2025, nilai ekonomi menggunakan referensi
-- satu bulan terakhir dan aset pada akhir bulan sebelumnya.
--
-- TUJUAN:
-- 1. Mengukur pengeluaran usaha baru.
-- 2. Mengukur pendapatan usaha baru.
-- 3. Mengetahui kontribusi pendapatan online.
-- 4. Mengetahui nilai aset usaha.
-- 5. Mengetahui struktur sumber modal ketika usaha didirikan.
--
-- UNIT DATA:
-- 1 baris = 1 usaha Ditemukan / Baru
--           yang mulai beroperasi tahun 2026
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
-- + index1
--
-- CAKUPAN:
-- Kabupaten Bulungan
-- Status usaha = Ditemukan / Baru
-- Tahun mulai operasi = 2026
-- Assignment aktif
--
-- JUMLAH KOLOM:
-- 25 / 25
-- ============================================================

SELECT

    /* ========================================================
       A. KEY USAHA
       ======================================================== */

    /* 01 */
    u.assignment_id,

    /* 02 */
    u.assignment_date_modified,

    /* 03 */
    u.index1,


    /* ========================================================
       B. TAHUN MULAI OPERASI
       ======================================================== */

    /* 04 */
    u.tahun_operasi
        AS tahun_mulai_operasi,


    /* ========================================================
       C. PENGELUARAN SATU BULAN TERAKHIR
       ======================================================== */

    /* 05 */
    u.gaji_bln
        AS pengeluaran_gaji_jaminan_sosial_bln,

    /* 06 */
    u.biaya_produksi_bln
        AS biaya_produksi_bln,

    /* 07 */
    u.biaya_pembelian_bln
        AS biaya_pembelian_barang_terjual_bln,

    /* 08 */
    u.operasional_bln
        AS biaya_operasional_bln,

    /* 09 */
    u.non_operasional_bln
        AS biaya_non_operasional_bln,

    /* 10 */
    u.total_pengeluaran_bln
        AS total_pengeluaran_bln,


    /* ========================================================
       D. PENDAPATAN SATU BULAN TERAKHIR
       ======================================================== */

    /* 11 */
    u.nilai_pendapatan_bln
        AS pendapatan_utama_bln,

    /* 12 */
    u.pendapatan_lain_bln
        AS pendapatan_lainnya_bln,

    /* 13 */
    u.total_pendapatan_bln
        AS total_pendapatan_bln,

    /* 14 */
    u.pendapatan_online_bln
        AS persen_pendapatan_online_bln,


    /* ========================================================
       E. ASET PADA AKHIR BULAN SEBELUMNYA
       ======================================================== */

    /* 15 */
    u.aset_tanah_bln
        AS aset_tanah_bangunan_bln,

    /* 16 */
    u.aset_lain_bln
        AS aset_selain_tanah_bangunan_bln,

    /* 17 */
    u.total_aset_bln
        AS total_aset_bln,

    /* 18 */
    u.rentang_aset_bln_value
        AS kode_rentang_aset_bln,

    /* 19 */
    u.luas_tanah_bln
        AS luas_tanah_usaha_m2,


    /* ========================================================
       F. SUMBER MODAL SAAT USAHA DIDIRIKAN
       Seluruh nilai merupakan persentase.
       ======================================================== */

    /* 20 */
    u.pribadi_didirikan
        AS modal_pribadi_persen,

    /* 21 */
    u.nonprofit_didirikan
        AS modal_nonprofit_persen,

    /* 22 */
    u.publik_didirikan
        AS modal_korporasi_publik_persen,

    /* 23 */
    u.nonpublik_didirikan
        AS modal_korporasi_nonpublik_persen,

    /* 24 */
    u.pemerintah_didirikan
        AS modal_pemerintah_persen,

    /* 25 */
    u.asing_didirikan
        AS modal_asing_persen


FROM tgr_fd68e454.se2026_nested u

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON u.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'

    AND u.keberadaan_usaha_value IN ('1', '2')

    AND TRIM(CAST(u.tahun_operasi AS STRING)) = '2026'

ORDER BY
    u.assignment_id,
    u.index1;
