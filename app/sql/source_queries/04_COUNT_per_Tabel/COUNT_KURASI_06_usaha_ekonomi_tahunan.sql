-- COUNT PRESISI: mengikuti FROM/JOIN/WHERE query data, tanpa menghitung kolom SELECT.
SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.se2026_nested u

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON u.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'

    AND u.keberadaan_usaha_value IN ('1', '2')

    AND NULLIF(
            TRIM(CAST(u.tahun_operasi AS STRING)),
            ''
        ) IS NOT NULL

    AND CAST(u.tahun_operasi AS INT) < 2026;
