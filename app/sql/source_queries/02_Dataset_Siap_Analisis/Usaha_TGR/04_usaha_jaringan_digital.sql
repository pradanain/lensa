-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [04_USAHA_JARINGAN_DIGITAL]
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
       B. JARINGAN USAHA
       ======================================================== */

    /* 04 */
    u.jaringan_value
        AS kode_jaringan_usaha,

    /* 05 */
    u.jaringan_label
        AS jaringan_usaha,

    /* 06 */
    u.jumlah_kc
        AS jumlah_kantor_cabang_unit,


    /* ========================================================
       C. KANTOR PUSAT
       ======================================================== */

    /* 07 */
    NULLIF(TRIM(u.nama_kp), '')
        AS nama_kantor_pusat,

    /* 08 */
    NULLIF(TRIM(u.alamat_kp), '')
        AS alamat_kantor_pusat,

    /* 09 */
    NULLIF(TRIM(u.email_kp), '')
        AS email_kantor_pusat,

    /* 10 */
    u.negara_kp_value
        AS kode_negara_kantor_pusat,

    /* 11 */
    u.negara_kp_label
        AS negara_kantor_pusat,

    /* 12 */
    u.prov_kp_value
        AS kode_provinsi_kantor_pusat,

    /* 13 */
    u.prov_kp_label
        AS provinsi_kantor_pusat,

    /* 14 */
    u.kab_kp_value
        AS kode_kabupaten_kantor_pusat,

    /* 15 */
    u.kab_kp_label
        AS kabupaten_kantor_pusat,


    /* ========================================================
       D. PENGGUNAAN INTERNET
       ======================================================== */

    /* 16 */
    u.internet_value
        AS kode_menggunakan_internet,

    /* 17 */
    u.internet_label
        AS menggunakan_internet,

    /* 18 */
    u.internet_pesanan_value
        AS internet_menerima_pesanan,

    /* 19 */
    u.internet_produksi_value
        AS internet_produksi,

    /* 20 */
    u.internet_distribusi_value
        AS internet_distribusi,

    /* 21 */
    u.internet_beli_value
        AS internet_pembelian_bahan_baku,

    /* 22 */
    u.internet_promosi_value
        AS internet_promosi,

    /* 23 */
    u.internet_lainnya_value
        AS internet_lainnya,


    /* ========================================================
       E. TEKNOLOGI DIGITAL
       ======================================================== */

    /* 24 */
    u.digital_value
        AS kode_teknologi_digital,

    /* 25 */
    u.digital_label
        AS teknologi_digital


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
