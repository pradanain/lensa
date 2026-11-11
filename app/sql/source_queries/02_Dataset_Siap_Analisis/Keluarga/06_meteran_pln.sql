-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [06_METERAN_PLN]
--
-- UNIT:
-- 1 baris = 1 meteran listrik pada roster keluarga
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
-- + index1
--
-- JUMLAH KOLOM: 14
-- ============================================================

SELECT

    /* 01 */
    m.assignment_id,

    /* 02 */
    m.assignment_date_modified,

    /* 03 */
    m.index1
        AS index_meteran,

    /* 04 */
    m.urutan_meteran_lain
        AS urutan_meteran,

    /* 05 */
    r.sumber_penerangan_value
        AS kode_sumber_penerangan,

    /* 06 */
    r.sumber_penerangan_label
        AS sumber_penerangan,

    /* 07 */
    r.jml_meteran
        AS jumlah_meteran_keluarga,

    /* 08 */
    m.daya_terpasang_value
        AS kode_daya_terpasang,

    /* 09 */
    m.daya_terpasang_label
        AS daya_terpasang,

    /* 10 */
    m.id_pln_pilih_value
        AS kode_jenis_identitas_pln,

    /* 11 */
    m.id_pln_pilih_label
        AS jenis_identitas_pln,

    /* 12 */
    NULLIF(TRIM(m.id_pelanggan), '')
        AS id_pelanggan_pln,

    /* 13 */
    NULLIF(TRIM(m.no_meteran), '')
        AS nomor_meteran,

    /* 14 */
    CASE
        WHEN NULLIF(TRIM(m.id_pelanggan), '') IS NOT NULL
          OR NULLIF(TRIM(m.no_meteran), '') IS NOT NULL
            THEN 1
        ELSE 0
    END AS identitas_pln_tersedia

FROM tgr_fd68e454.nested_meteran m

INNER JOIN tgr_fd68e454.root_table r
    ON m.assignment_id = r.assignment_id
   AND m.assignment_date_modified = r.assignment_date_modified

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON m.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'
    AND r.ada_keluarga_value IN ('1', '2')

ORDER BY
    m.assignment_id,
    m.index1;
