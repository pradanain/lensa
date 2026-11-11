-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- DATASET : 08C_DATA_DARI_KANTOR_PUSAT
-- JENIS   : DATA
--
-- DESKRIPSI:
-- Data assignment bangunan/usaha yang berstatus:
-- 7 = Data diperoleh dari Kantor Pusat (KP).
--
-- TUJUAN:
-- 1. Mengambil seluruh assignment status 7.
-- 2. Mengetahui identitas bangunan/usaha.
-- 3. Mempertahankan alamat dan status assignment.
-- 4. Menjadi dasar crosscheck dengan usaha berjaringan.
--
-- GOAL:
-- Memastikan assignment status 7 tidak terlewat pada
-- saat penggabungan seluruh data SE2026.
--
-- UNIT:
-- 1 baris = 1 assignment
--
-- KEY:
-- assignment_id + assignment_date_modified
--
-- FILTER:
-- Kabupaten Bulungan
-- Status keberadaan bangunan/usaha = 7
--
-- KOLOM: 9 / 25
-- ============================================================

SELECT

    /* A. KEY */

    /* 01 */
    r.assignment_id,

    /* 02 */
    r.assignment_date_modified,

    /* 03 */
    a.code_identity,


    /* B. IDENTITAS BANGUNAN / USAHA */

    /* 04 */
    r.nama_usaha_bang AS nama_bangunan_usaha,


    /* C. STATUS KEBERADAAN */

    /* 05 */
    r.ada_bang_usaha_value AS kode_keberadaan,

    /* 06 */
    r.ada_bang_usaha_label AS status_keberadaan,


    /* D. ALAMAT */

    /* 07 */
    r.alamat_prelist AS alamat_prelist,

    /* 08 */
    r.jalan_domisili AS jalan_domisili,


    /* E. STATUS ASSIGNMENT */

    /* 09 */
    a.assignment_status_alias AS status_assignment

FROM tgr_fd68e454.root_table r

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON r.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'

    AND r.ada_bang_usaha_value = '7'

ORDER BY
    r.assignment_id;
