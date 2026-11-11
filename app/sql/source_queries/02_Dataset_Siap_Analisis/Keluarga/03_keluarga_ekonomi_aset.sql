-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [03_KELUARGA_EKONOMI_ASET]
--
-- UNIT:
-- 1 baris = 1 keluarga Ditemukan / Baru
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
--
-- JUMLAH KOLOM: 25
-- ============================================================

SELECT

    /* ========================================================
       A. KEY
       ======================================================== */

    /* 01 */
    r.assignment_id,

    /* 02 */
    r.assignment_date_modified,


    /* ========================================================
       B. EKONOMI KELUARGA
       ======================================================== */

    /* 03 */
    r.total_pendapatan_keluarga_sebulan
        AS total_pendapatan_keluarga_sebulan,

    /* 04 */
    r.total_pengeluaran_keluarga_sebulan
        AS total_pengeluaran_keluarga_sebulan,

    /* 05 */
    r.listrik_sebulan
        AS pengeluaran_listrik_sebulan,

    /* 06 */
    r.pulsa_sebulan
        AS pengeluaran_pulsa_internet_sebulan,

    /* 07 */
    r.pengeluaran_makanan_mingguan,

    /* 08 */
    r.pengeluaran_non_makan_bulanan,

    /* 09 */
    r.pengeluaran_non_makan_tahunan,


    /* ========================================================
       C. KONTEKS LISTRIK
       ======================================================== */

    /* 10 */
    r.sumber_penerangan_value
        AS sumber_penerangan,

    /* 11 */
    r.jml_meteran
        AS jumlah_meteran,


    /* ========================================================
       D. ASET KELUARGA
       ======================================================== */

    /* 12 */
    r.jumlah_tabung3kg_new
        AS jumlah_tabung_lpg_3kg,

    /* 13 */
    r.jumlah_tabung5kg_new
        AS jumlah_tabung_lpg_5kg_lebih,

    /* 14 */
    r.jumlah_kulkas_new
        AS jumlah_kulkas,

    /* 15 */
    r.jumlah_ac_new
        AS jumlah_ac,

    /* 16 */
    r.jumlah_emas_new
        AS jumlah_emas_gram,

    /* 17 */
    r.jumlah_laptop_new
        AS jumlah_komputer_laptop_tablet,

    /* 18 */
    r.jumlah_motor_new
        AS jumlah_sepeda_motor,

    /* 19 */
    r.nilai_motor
        AS nilai_aset_sepeda_motor,

    /* 20 */
    r.jumlah_mobil_new
        AS jumlah_mobil,

    /* 21 */
    r.nilai_mobil
        AS nilai_aset_mobil,

    /* 22 */
    r.jumlah_lahan_new
        AS jumlah_lahan_lain,

    /* 23 */
    r.nilai_lahan
        AS nilai_aset_lahan_lain,

    /* 24 */
    r.jumlah_rumah_new
        AS jumlah_rumah_bangunan_lain,

    /* 25 */
    r.nilai_rumah
        AS nilai_aset_rumah_bangunan_lain


FROM tgr_fd68e454.root_table r

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON r.assignment_id = a.assignment_id

WHERE
    a.level_2_full_code = '6502'
    AND a.is_active = 1
    AND r.ada_keluarga_value IN ('1', '2')

ORDER BY
    r.assignment_id;
