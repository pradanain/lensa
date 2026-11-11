-- =====================================================
-- MASTER USAHA BESAR (UB) SE2026 - KABUPATEN BULUNGAN
-- QUERY A: IDENTITAS DAN PROFIL USAHA
-- 25 KOLOM
-- =====================================================

WITH ub_versi AS (
    SELECT
        r.assignment_id,
        r.kec_l_label,
        r.desa_l_label,
        r.kode_desa_full,
        r.nama_usaha,
        r.nama_komersial,
        r.alamat_usaha,
        r.geotag_pml_latitude,
        r.geotag_pml_longitude,
        r.idsbr,
        r.nib,
        r.keberadaan_label,
        r.badan_usaha_label,
        r.kbli_akhir,
        r.keg_utama,
        r.produk,
        r.jaringan_label,
        r.nama_kp,
        r.alamat_kp,
        r.nama_pj,
        r.nik_pj,
        r.jk_pj_label,
        r.umur_pj,
        r.hp,
        r.email,
        ROW_NUMBER() OVER (
            PARTITION BY r.assignment_id
            ORDER BY r.assignment_date_modified DESC,
                     r.assignment_id_timestamp DESC
        ) AS urut_versi
    FROM tcz_37526b20.root_table r
    INNER JOIN tcz_37526b20.base_table_assignment a
        ON a.assignment_id = r.assignment_id
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
)

SELECT

    -- ===== IDENTITAS DAN STATUS USAHA =====
    -- 01. id_penghubung
    r.assignment_id AS id_penghubung,
    -- 02. nama_usaha
    r.nama_usaha AS nama_usaha,
    -- 03. nama_komersial
    r.nama_komersial AS nama_komersial,
    -- 04. status_keberadaan
    REGEXP_REPLACE(r.keberadaan_label, '<[^>]*>', '') AS status_keberadaan,

    -- ===== WILAYAH DAN LOKASI USAHA =====
    -- 05. kode_desa
    CASE
        WHEN LEFT(r.kec_l_label, 1) = '['
         AND SUBSTRING(r.kec_l_label, 5, 1) = ']'
         AND LEFT(r.desa_l_label, 1) = '['
         AND SUBSTRING(r.desa_l_label, 5, 1) = ']'
         AND SUBSTRING(r.kec_l_label, 2, 3) REGEXP '^[0-9]{3}$'
         AND SUBSTRING(r.desa_l_label, 2, 3) REGEXP '^[0-9]{3}$'
         AND SUBSTRING(r.kec_l_label, 2, 3) <> '000'
         AND SUBSTRING(r.desa_l_label, 2, 3) <> '000'
        THEN CONCAT('6502', SUBSTRING(r.kec_l_label, 2, 2), '0',
                    SUBSTRING(r.desa_l_label, 2, 3))
        ELSE COALESCE(
            NULLIF(NULLIF(TRIM(r.kode_desa_full), ''), '6502000000'),
            NULLIF(NULLIF(TRIM(a.level_4_full_code), ''), '6502000000'),
            NULLIF(TRIM(r.kode_desa_full), ''),
            NULLIF(TRIM(a.level_4_full_code), '')
        )
    END AS kode_desa,
    -- 06. kecamatan
    COALESCE(
        CASE WHEN LOWER(TRIM(SUBSTRING_INDEX(r.kec_l_label, ']', -1))) IN ('', 'null', '-')
             THEN NULL ELSE TRIM(SUBSTRING_INDEX(r.kec_l_label, ']', -1)) END,
        CASE WHEN LOWER(TRIM(SUBSTRING_INDEX(a.level_3_name, ']', -1))) IN ('', 'null', '-')
             THEN NULL ELSE TRIM(SUBSTRING_INDEX(a.level_3_name, ']', -1)) END,
        '-'
    ) AS kecamatan,
    -- 07. desa_kelurahan
    COALESCE(
        CASE WHEN LOWER(TRIM(SUBSTRING_INDEX(r.desa_l_label, ']', -1))) IN ('', 'null', '-')
             THEN NULL ELSE TRIM(SUBSTRING_INDEX(r.desa_l_label, ']', -1)) END,
        CASE WHEN LOWER(TRIM(SUBSTRING_INDEX(a.level_4_name, ']', -1))) IN ('', 'null', '-')
             THEN NULL ELSE TRIM(SUBSTRING_INDEX(a.level_4_name, ']', -1)) END,
        '-'
    ) AS desa_kelurahan,
    -- 08. alamat_usaha
    r.alamat_usaha AS alamat_usaha,
    -- 09. link_google_maps
    -- GPS PML yang valid, lalu koordinat assignment (fallback).
    CASE
        WHEN TRIM(CAST(r.geotag_pml_latitude AS CHAR)) REGEXP '^-?[0-9]+([.][0-9]+)?$'
         AND TRIM(CAST(r.geotag_pml_longitude AS CHAR)) REGEXP '^-?[0-9]+([.][0-9]+)?$'
         AND CAST(r.geotag_pml_latitude AS DECIMAL(13,8)) BETWEEN -90 AND 90
         AND CAST(r.geotag_pml_longitude AS DECIMAL(13,8)) BETWEEN -180 AND 180
         AND NOT (CAST(r.geotag_pml_latitude AS DECIMAL(13,8)) = 0 AND CAST(r.geotag_pml_longitude AS DECIMAL(13,8)) = 0)
        THEN CONCAT('https://www.google.com/maps/search/?api=1&query=',
                    TRIM(CAST(r.geotag_pml_latitude AS CHAR)), ',',
                    TRIM(CAST(r.geotag_pml_longitude AS CHAR)))
        WHEN TRIM(CAST(a.latitude AS CHAR)) REGEXP '^-?[0-9]+([.][0-9]+)?$'
         AND TRIM(CAST(a.longitude AS CHAR)) REGEXP '^-?[0-9]+([.][0-9]+)?$'
         AND CAST(a.latitude AS DECIMAL(13,8)) BETWEEN -90 AND 90
         AND CAST(a.longitude AS DECIMAL(13,8)) BETWEEN -180 AND 180
         AND NOT (CAST(a.latitude AS DECIMAL(13,8)) = 0 AND CAST(a.longitude AS DECIMAL(13,8)) = 0)
        THEN CONCAT('https://www.google.com/maps/search/?api=1&query=',
                    TRIM(CAST(a.latitude AS CHAR)), ',',
                    TRIM(CAST(a.longitude AS CHAR)))
        ELSE NULL
    END AS link_google_maps,

    -- ===== IDENTIFIKASI DAN LEGALITAS =====
    -- 10. id_sbr
    r.idsbr AS id_sbr,
    -- 11. nib
    NULLIF(TRIM(CAST(r.nib AS CHAR)), '') AS nib,
    -- 12. badan_usaha
    REGEXP_REPLACE(r.badan_usaha_label, '<[^>]*>', '') AS badan_usaha,

    -- ===== KLASIFIKASI DAN KEGIATAN =====
    -- 13. kbli_akhir
    r.kbli_akhir AS kbli_akhir,
    -- 14. kategori_kbli
    CASE
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '01' AND '03' THEN 'A'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '05' AND '09' THEN 'B'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '10' AND '33' THEN 'C'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) = '35' THEN 'D'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '36' AND '39' THEN 'E'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '41' AND '43' THEN 'F'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '45' AND '47' THEN 'G'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '49' AND '53' THEN 'H'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '55' AND '56' THEN 'I'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '58' AND '60' THEN 'J'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '61' AND '63' THEN 'K'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '64' AND '66' THEN 'L'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) = '68' THEN 'M'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '69' AND '75' THEN 'N'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '77' AND '82' THEN 'O'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) = '84' THEN 'P'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) = '85' THEN 'Q'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '86' AND '88' THEN 'R'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '90' AND '93' THEN 'S'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '94' AND '96' THEN 'T'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) BETWEEN '97' AND '98' THEN 'U'
        WHEN LEFT(TRIM(r.kbli_akhir), 2) = '99' THEN 'V'
        ELSE NULL
    END AS kategori_kbli,
    -- 15. kegiatan_utama
    r.keg_utama AS kegiatan_utama,
    -- 16. produk_utama
    r.produk AS produk_utama,

    -- ===== JARINGAN DAN KANTOR PUSAT =====
    -- 17. jaringan_usaha
    REGEXP_REPLACE(r.jaringan_label, '<[^>]*>', '') AS jaringan_usaha,
    -- 18. nama_kantor_pusat
    r.nama_kp AS nama_kantor_pusat,
    -- 19. alamat_kantor_pusat
    r.alamat_kp AS alamat_kantor_pusat,

    -- ===== PENANGGUNG JAWAB DAN KONTAK =====
    -- 20. nama_penanggung_jawab
    r.nama_pj AS nama_penanggung_jawab,
    -- 21. nik_penanggung_jawab
    NULLIF(TRIM(CAST(r.nik_pj AS CHAR)), '') AS nik_penanggung_jawab,
    -- 22. jenis_kelamin_penanggung_jawab
    REGEXP_REPLACE(r.jk_pj_label, '<[^>]*>', '') AS jenis_kelamin_penanggung_jawab,
    -- 23. umur_penanggung_jawab
    r.umur_pj AS umur_penanggung_jawab,
    -- 24. nomor_hp_usaha
    r.hp AS nomor_hp_usaha,
    -- 25. email_usaha
    r.email AS email_usaha
FROM tcz_37526b20.base_table_assignment a
INNER JOIN ub_versi r ON a.assignment_id = r.assignment_id
WHERE a.is_active = 1
  AND a.level_2_full_code = '6502'
  AND r.urut_versi = 1
ORDER BY id_penghubung;
