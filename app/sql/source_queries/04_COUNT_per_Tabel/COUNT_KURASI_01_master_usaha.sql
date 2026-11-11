-- COUNT PRESISI: mengikuti FROM/JOIN/WHERE query data, tanpa menghitung kolom SELECT.
SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.se2026_nested u

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON u.assignment_id = a.assignment_id
   AND a.is_active = 1

LEFT JOIN tgr_fd68e454.root_table r
    ON u.assignment_id = r.assignment_id
   AND u.assignment_date_modified = r.assignment_date_modified

WHERE
    a.level_2_full_code = '6502'

    -- Hanya item roster yang benar-benar mempunyai
    -- jawaban keberadaan usaha
    AND u.keberadaan_usaha_value IS NOT NULL;
