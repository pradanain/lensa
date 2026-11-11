-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [04_ANGGOTA_KELUARGA]
--
-- UNIT:
-- 1 baris = 1 anggota keluarga
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
-- + index1
--
-- CAKUPAN:
-- Keluarga Ditemukan / Baru
--
-- JUMLAH KOLOM: 25
-- ============================================================

SELECT

    /* ========================================================
       A. KEY
       ======================================================== */

    /* 01 */
    d.assignment_id,

    /* 02 */
    d.assignment_date_modified,

    /* 03 */
    d.index1,


    /* ========================================================
       B. IDENTITAS ANGGOTA
       ======================================================== */

    /* 04 */
    d.no_urut_kk
        AS nomor_urut_anggota,

    /* 05 */
    NULLIF(TRIM(d.nama_dtsen), '')
        AS nama_anggota,

    /* 06 */
    NULLIF(TRIM(d.nik_dtsen), '')
        AS nik_anggota,


    /* ========================================================
       C. HUBUNGAN DENGAN KEPALA KELUARGA
       ======================================================== */

    /* 07 */
    d.hubungan_value
        AS kode_hubungan,

    /* 08 */
    d.hubungan_label
        AS hubungan_kepala_keluarga,


    /* ========================================================
       D. KEBERADAAN / DOMISILI
       ======================================================== */

    /* 09 */
    d.keberadaan_dtsen_value
        AS kode_keberadaan_anggota,

    /* 10 */
    d.keberadaan_dtsen_label
        AS keberadaan_anggota,

    /* 11 */
    d.alamat_dn_value
        AS kode_domisili,

    /* 12 */
    d.prov_dn_value
        AS provinsi_domisili,

    /* 13 */
    d.kab_dn_value
        AS kabupaten_domisili,

    /* 14 */
    d.domisili_ln_value
        AS negara_domisili_luar_negeri,


    /* ========================================================
       E. STATUS PERKAWINAN
       ======================================================== */

    /* 15 */
    d.status_kawin_value
        AS kode_status_perkawinan,

    /* 16 */
    d.status_kawin_label
        AS status_perkawinan,


    /* ========================================================
       F. JENIS KELAMIN
       ======================================================== */

    /* 17 */
    d.jk_dtsen_value
        AS kode_jenis_kelamin,

    /* 18 */
    d.jk_dtsen_label
        AS jenis_kelamin,


    /* ========================================================
       G. KELAHIRAN & UMUR
       ======================================================== */

    /* 19 */
    d.tgl_lahir
        AS tanggal_lahir_hari,

    /* 20 */
    d.bln_lahir_value
        AS bulan_lahir,

    /* 21 */
    d.thn_lahir
        AS tahun_lahir,

    /* 22 */
    d.umur_ak
        AS umur,


    /* ========================================================
       H. KEPEMILIKAN USAHA
       ======================================================== */

    /* 23 */
    d.art_ada_usaha_value
        AS kode_memiliki_usaha,

    /* 24 */
    d.art_ada_usaha_label
        AS memiliki_usaha,


    /* ========================================================
       I. SUMBER ANGGOTA
       ======================================================== */

    /* 25 */
    d.isprelistart
        AS anggota_prelist


FROM tgr_fd68e454.nested_dtsen d

INNER JOIN tgr_fd68e454.root_table r
    ON d.assignment_id = r.assignment_id
   AND d.assignment_date_modified = r.assignment_date_modified

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON d.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'
    AND r.ada_keluarga_value IN ('1', '2')

ORDER BY
    d.assignment_id,
    d.index1;
