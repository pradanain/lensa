-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [02_KELUARGA_PERUMAHAN]
--
-- KARAKTERISTIK PERUMAHAN KELUARGA SE2026
-- KABUPATEN BULUNGAN
--
-- UNIT:
-- 1 baris = 1 keluarga Ditemukan / Baru
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
--
-- CATATAN:
-- - Tidak mengulang wilayah/nama KK dari MASTER
-- - Menggunakan _value untuk pertanyaan kategori
-- - Tepat 25 kolom
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
       B. JENIS BANGUNAN
       ======================================================== */

    /* 03
       Jenis bangunan tempat tinggal
       ======================================================== */
    r.jns_bangunan_value AS jenis_bangunan,

    /* 04
       Isian jika jenis bangunan = lainnya
       ======================================================== */
    r.jns_bangunan_lain AS jenis_bangunan_lainnya,

    /* 05
       Nama / nomor lantai apartemen atau rumah susun
       ======================================================== */
    r.nm_apt AS nama_apartemen_rusun,


    /* ========================================================
       C. KEPEMILIKAN TEMPAT TINGGAL
       ======================================================== */

    /* 06 */
    r.status_kepemilikan_value AS status_kepemilikan,

    /* 07 */
    r.bukti_kepemilikan_value AS bukti_kepemilikan,

    /* 08
       Perkiraan sewa jika milik sendiri / bebas sewa
       ======================================================== */
    r.sewa_sendiri,

    /* 09 */
    r.sewa_kontrak,

    /* 10 */
    r.sewa_dinas,


    /* ========================================================
       D. KONDISI FISIK BANGUNAN
       ======================================================== */

    /* 11 */
    r.luas_lantai,

    /* 12 */
    r.jns_lantai_value AS jenis_lantai,

    /* 13 */
    r.kondisi_lantai_value AS kondisi_lantai,

    /* 14 */
    r.jns_dinding_value AS jenis_dinding,

    /* 15 */
    r.kondisi_dinding_value AS kondisi_dinding,

    /* 16 */
    r.jns_atap_value AS jenis_atap,

    /* 17 */
    r.kondisi_atap_value AS kondisi_atap,


    /* ========================================================
       E. SANITASI & AIR MINUM
       ======================================================== */

    /* 18 */
    r.tempat_bab_value AS fasilitas_bab,

    /* 19 */
    r.jns_closet_value AS jenis_kloset,

    /* 20 */
    r.buang_tinja_value AS pembuangan_akhir_tinja,

    /* 21 */
    r.air_minum_value AS sumber_air_minum,


    /* ========================================================
       F. LISTRIK & KOMUNIKASI
       ======================================================== */

    /* 22 */
    r.sumber_penerangan_value AS sumber_penerangan,

    /* 23 */
    r.jml_meteran AS jumlah_meteran,

    /* 24 */
    r.listrik_sebulan AS pengeluaran_listrik_sebulan,

    /* 25 */
    r.pulsa_sebulan AS pengeluaran_pulsa_internet_sebulan


FROM tgr_fd68e454.root_table r

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON r.assignment_id = a.assignment_id

WHERE
    a.level_2_full_code = '6502'
    AND a.is_active = 1

    -- Keluarga substantif
    AND r.ada_keluarga_value IN ('1', '2')

ORDER BY
    r.assignment_id;
