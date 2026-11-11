-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- DATASET : 08B_KANTOR_UNIT_ROSTER
-- JENIS   : DATA
--
-- DESKRIPSI:
-- Data rincian kantor cabang dan unit pembantu/penunjang
-- yang didaftarkan dalam roster kantor/unit SE2026.
--
-- TUJUAN:
-- 1. Mengidentifikasi kantor/unit dari usaha induk.
-- 2. Memisahkan setiap unit berdasarkan index2.
-- 3. Mengetahui lokasi kantor/unit.
-- 4. Mengambil pekerja dan nilai ekonomi masing-masing unit.
--
-- GOAL:
-- Membentuk dataset detail kantor/unit yang dapat
-- dihubungkan dengan master usaha.
--
-- UNIT:
-- 1 baris = 1 kantor/unit
--
-- KEY:
-- assignment_id + assignment_date_modified
-- + index_usaha + index_kantor_unit
--
-- FILTER:
-- Induk usaha Ditemukan/Baru
-- Kabupaten Bulungan
--
-- KOLOM: 19 / 25
-- ============================================================

SELECT

    /* A. KEY */

    /* 01 */
    k.assignment_id,

    /* 02 */
    k.assignment_date_modified,

    /* 03 */
    k.index1 AS index_usaha,

    /* 04 */
    k.index2 AS index_kantor_unit,


    /* B. IDENTITAS KANTOR / UNIT */

    /* 05 */
    k.kp_unit AS nama_kantor_unit,

    /* 06 */
    k.kp_jenis_value AS kode_jenis_unit,

    /* 07 */
    k.kp_jenis_label AS jenis_unit,


    /* C. LOKASI KANTOR / UNIT */

    /* 08 */
    k.kp_prov_value AS kode_provinsi_unit,

    /* 09 */
    k.kp_prov_label AS provinsi_unit,

    /* 10 */
    k.kp_kab_value AS kode_kabupaten_unit,

    /* 11 */
    k.kp_kab_label AS kabupaten_unit,


    /* D. KARAKTERISTIK LINGKUNGAN */

    /* 12 */
    k.kp_produksi_lingkungan_value
        AS kode_produk_ramah_lingkungan,

    /* 13 */
    k.kp_produksi_lingkungan_label
        AS produk_ramah_lingkungan,

    /* 14 */
    k.kp_perlindungan_lingkungan_value
        AS kode_biaya_perlindungan_lingkungan,

    /* 15 */
    k.kp_perlindungan_lingkungan_label
        AS biaya_perlindungan_lingkungan,


    /* E. PEKERJA DAN EKONOMI UNIT */

    /* 16 */
    k.kp_tk AS jumlah_pekerja_unit_2025,

    /* 17 */
    k.kp_total_pengeluaran
        AS pengeluaran_unit_2025,

    /* 18 */
    k.kp_total_pendapatan
        AS pendapatan_unit_2025,

    /* 19 */
    k.kp_total_aset
        AS aset_unit_2025

FROM tgr_fd68e454.kp_nested k

INNER JOIN tgr_fd68e454.se2026_nested u
    ON k.assignment_id = u.assignment_id
   AND k.assignment_date_modified = u.assignment_date_modified
   AND k.index1 = u.index1

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON k.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'

    AND u.keberadaan_usaha_value IN ('1', '2')

ORDER BY
    k.assignment_id,
    k.index1,
    k.index2;
