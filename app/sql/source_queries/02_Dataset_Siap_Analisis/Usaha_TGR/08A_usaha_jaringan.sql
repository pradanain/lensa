-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- DATASET : 08A_USAHA_JARINGAN
-- JENIS   : DATA
--
-- DESKRIPSI:
-- Master usaha yang memiliki klasifikasi jaringan:
-- kantor pusat, cabang, perwakilan, pabrik, dan unit
-- pembantu/penunjang di Kabupaten Bulungan.
--
-- TUJUAN:
-- 1. Mengidentifikasi seluruh usaha berjaringan.
-- 2. Memetakan jenis jaringan usaha.
-- 3. Mengidentifikasi usaha cabang dan unit penunjang.
-- 4. Mengetahui informasi kantor pusat yang terkait.
-- 5. Mendukung crosscheck jaringan usaha D2D/TGR.
--
-- UNIT:
-- 1 baris = 1 usaha
--
-- KEY:
-- assignment_id + assignment_date_modified + index_usaha
--
-- FILTER:
-- Kabupaten Bulungan
-- Status Ditemukan/Baru
-- Jaringan 2, 3, 4, 5, 6
--
-- KOLOM: 24 / 25
-- ============================================================

SELECT

    /* A. KEY DAN IDENTITAS */

    /* 01 */ u.assignment_id,
    /* 02 */ u.assignment_date_modified,
    /* 03 */ u.index1 AS index_usaha,
    /* 04 */ a.code_identity,

    /* B. NAMA USAHA */

    /* 05 */ u.nama_usaha AS nama_usaha_prelist,
    /* 06 */ u.nama_usaha_edit AS nama_usaha_edit,
    /* 07 */ u.nama_komersial AS nama_komersial,

    /* C. STATUS KEBERADAAN */

    /* 08 */
    u.keberadaan_usaha_value AS kode_status_usaha,

    /* 09 */
    u.keberadaan_usaha_label AS status_usaha,

    /* D. KLASIFIKASI JARINGAN */

    /* 10 */
    u.jaringan_value AS kode_jaringan,

    /* 11 */
    u.jaringan_label AS jenis_jaringan,

    /* E. KBLI */

    /* 12 */
    u.kategori AS kategori_kbli,

    /* 13 */
    u.kbli_akhir AS kbli_akhir,

    /* F. LOKASI USAHA */

    /* 14 */
    u.alamat_usaha_view AS alamat_usaha,

    /* 15 */
    u.kec_l AS kecamatan,

    /* 16 */
    u.desa_l AS desa_kelurahan,

    /* 17 */
    u.kodesls_l AS kode_sls_subsls,

    /* G. INFORMASI KANTOR PUSAT */

    /* 18 */
    u.jumlah_kc AS jumlah_cabang_unit_dilaporkan,

    /* 19 */
    u.nama_kp AS nama_kantor_pusat,

    /* 20 */
    u.alamat_kp AS alamat_kantor_pusat,

    /* 21 */
    u.email_kp AS email_kantor_pusat,

    /* 22 */
    u.negara_kp_value AS kode_negara_kp,

    /* 23 */
    u.prov_kp_value AS kode_provinsi_kp,

    /* 24 */
    u.kab_kp_value AS kode_kabupaten_kp

FROM tgr_fd68e454.se2026_nested u

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON u.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'

    AND u.keberadaan_usaha_value IN ('1', '2')

    AND u.jaringan_value IN ('2', '3', '4', '5', '6')

ORDER BY
    u.jaringan_value,
    u.assignment_id,
    u.index1;
