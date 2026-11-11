-- ======================================================================
-- MASTER ASSIGNMENT TCZ_UB - 1 BARIS PER ASSIGNMENT
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Seluruh assignment aktif termasuk EC; NULL root dipertahankan.
-- ======================================================================

WITH assignment_aktif AS (
    SELECT
        a.`assignment_id` AS `assignment_id`,
        a.`assignment_date_modified` AS `assignment_date_modified`,
        a.`code_identity` AS `code_identity`,
        a.`listing` AS `listing_assignment`,
        a.`mode` AS `mode`,
        a.`assignment_status_alias` AS `status_assignment`,
        a.`assignment_status_id` AS `kode_status_assignment`,
        a.`date_created` AS `tanggal_dibuat`,
        a.`date_modified` AS `tanggal_diubah`,
        a.`done` AS `done`,
        a.`external_done` AS `external_done`,
        a.`source_from` AS `source_from`,
        a.`level_2_full_code` AS `kode_kabupaten`,
        a.`level_3_full_code` AS `kode_kecamatan`,
        a.`level_3_name` AS `kecamatan`,
        a.`level_4_full_code` AS `kode_desa`,
        a.`level_4_name` AS `desa_kelurahan`,
        a.`level_5_full_code` AS `kode_sls`,
        a.`level_5_name` AS `sls`,
        a.`level_6_full_code` AS `kode_subsls`,
        a.`level_6_name` AS `subsls`,
        a.`latitude` AS `latitude_assignment`,
        a.`longitude` AS `longitude_assignment`,
        ROW_NUMBER() OVER (
            PARTITION BY a.assignment_id
            ORDER BY a.assignment_date_modified DESC,
                     a.assignment_id_timestamp DESC
        ) AS urut_assignment
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
),
root_tersedia AS (
    SELECT
        r.assignment_id,
        MAX(r.assignment_date_modified) AS versi_root_terbaru
    FROM tcz_37526b20.root_table r
    WHERE r.assignment_id IN (
        SELECT a.assignment_id
        FROM tcz_37526b20.base_table_assignment a
        WHERE a.is_active = 1
          AND a.level_2_full_code = '6502'
    )
    GROUP BY r.assignment_id
)
SELECT
    m.`assignment_id`,
    m.`assignment_date_modified`,
    m.`code_identity`,
    m.`listing_assignment`,
    m.`mode`,
    m.`status_assignment`,
    m.`kode_status_assignment`,
    m.`tanggal_dibuat`,
    m.`tanggal_diubah`,
    m.`done`,
    m.`external_done`,
    m.`source_from`,
    m.`kode_kabupaten`,
    m.`kode_kecamatan`,
    m.`kecamatan`,
    m.`kode_desa`,
    m.`desa_kelurahan`,
    m.`kode_sls`,
    m.`sls`,
    m.`kode_subsls`,
    m.`subsls`,
    m.`latitude_assignment`,
    m.`longitude_assignment`,
    r.versi_root_terbaru,
    CASE WHEN r.assignment_id IS NULL
         THEN 'TANPA_KUESIONER'
         ELSE 'ADA_KUESIONER'
    END AS status_kuesioner
FROM assignment_aktif m
LEFT JOIN root_tersedia r
    ON m.assignment_id = r.assignment_id
WHERE m.urut_assignment = 1
ORDER BY m.assignment_id;
