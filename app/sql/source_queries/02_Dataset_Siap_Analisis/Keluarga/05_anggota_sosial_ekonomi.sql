-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [05_ANGGOTA_SOSIAL_EKONOMI]
--
-- SOSIAL EKONOMI ANGGOTA KELUARGA SE2026
-- KABUPATEN BULUNGAN
--
-- UNIT DATA:
-- 1 baris = 1 anggota keluarga pada Blok III
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
-- + index1
--
-- CAKUPAN:
-- Keluarga Ditemukan / Baru
--
-- JUMLAH KOLOM:
-- 25
--
-- CATATAN:
-- - Tidak mengambil PPL/PML
-- - Tidak JOIN ke nested_dtsen agar tidak berisiko
--   menyebabkan row multiplication
-- - total_pendapatan_pekerjaan dihitung numerik
--   dari seluruh komponen pendapatan pekerjaan
-- ============================================================

SELECT

    /* ========================================================
       A. KEY ANGGOTA
       ======================================================== */

    /* 01 */
    v.assignment_id,

    /* 02 */
    v.assignment_date_modified,

    /* 03 */
    v.index1,

    /* 04 */
    v.no_urut_kk_var
        AS nomor_urut_anggota,

    /* 05 */
    NULLIF(TRIM(v.nama_dtsen_var), '')
        AS nama_anggota,


    /* ========================================================
       B. PENDIDIKAN
       ======================================================== */

    /* 06 */
    v.sekolah_value
        AS kode_partisipasi_sekolah,

    /* 07 */
    v.sekolah_label
        AS partisipasi_sekolah,

    /* 08 */
    v.ijazah_value
        AS kode_ijazah_tertinggi,

    /* 09 */
    v.ijazah_label
        AS ijazah_tertinggi,


    /* ========================================================
       C. PEKERJAAN
       ======================================================== */

    /* 10 */
    v.profesi_value
        AS kode_profesi_utama,

    /* 11 */
    v.profesi_label
        AS profesi_utama,

    /* 12 */
    v.status_kerja_value
        AS kode_status_pekerjaan,


    /* ========================================================
       D. PENDAPATAN DARI PEKERJAAN
       ======================================================== */

    /* 13 */
    v.pendapatan_pekerjaan_value
        AS mempunyai_pendapatan_pekerjaan,

    /* 14 */
    v.pend_gaji
        AS pendapatan_gaji,

    /* 15 */
    v.pend_tunjangan
        AS pendapatan_tunjangan,

    /* 16 */
    v.pend_uangmkn
        AS pendapatan_uang_makan,

    /* 17 */
    v.pend_honor
        AS pendapatan_honor,

    /* 18 */
    v.pend_lembur
        AS pendapatan_lembur,

    /* 19 */
    v.pend_lainnya
        AS pendapatan_pekerjaan_lainnya,

    /* 20
       Total numerik:
       gaji + tunjangan + uang makan
       + honor + lembur + lainnya
       ======================================================== */
    CASE
        WHEN TRIM(CAST(v.pendapatan_pekerjaan_value AS STRING)) = '1'
        THEN
              COALESCE(v.pend_gaji, 0)
            + COALESCE(v.pend_tunjangan, 0)
            + COALESCE(v.pend_uangmkn, 0)
            + COALESCE(v.pend_honor, 0)
            + COALESCE(v.pend_lembur, 0)
            + COALESCE(v.pend_lainnya, 0)
        ELSE NULL
    END AS total_pendapatan_pekerjaan,


    /* ========================================================
       E. PENDAPATAN USAHA
       ======================================================== */

    /* 21 */
    v.pendapatan_usaha_value
        AS mempunyai_pendapatan_usaha,

    /* 22 */
    v.pend_usaha
        AS total_pendapatan_usaha,


    /* ========================================================
       F. PENDAPATAN LAIN
       ======================================================== */

    /* 23 */
    v.pend_usaha_lain_value
        AS mempunyai_pendapatan_lain,

    /* 24 */
    v.nilai_pend_lain
        AS total_pendapatan_lain,


    /* ========================================================
       G. INKLUSI KEUANGAN
       ======================================================== */

    /* 25 */
    v.rekening_value
        AS mempunyai_rekening_dompet_digital


FROM tgr_fd68e454.nested_dtsen_var v


/* ============================================================
   FILTER KELUARGA DITEMUKAN / BARU
   Root harus berasal dari versi questionnaire yang sama
   ============================================================ */

INNER JOIN tgr_fd68e454.root_table r
    ON v.assignment_id = r.assignment_id
   AND v.assignment_date_modified = r.assignment_date_modified


/* ============================================================
   ASSIGNMENT AKTIF
   ============================================================ */

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON v.assignment_id = a.assignment_id
   AND a.is_active = 1


WHERE

    /* Kabupaten Bulungan */
    a.level_2_full_code = '6502'

    /* Keluarga substantif */
    AND r.ada_keluarga_value IN ('1', '2')


ORDER BY
    v.assignment_id,
    v.index1;
