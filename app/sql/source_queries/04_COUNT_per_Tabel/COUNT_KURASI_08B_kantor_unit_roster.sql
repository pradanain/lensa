-- COUNT PRESISI: mengikuti FROM/JOIN/WHERE query data, tanpa menghitung kolom SELECT.
SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.kp_nested k

INNER JOIN tgr_fd68e454.se2026_nested u
    ON k.assignment_id = u.assignment_id
   AND k.assignment_date_modified = u.assignment_date_modified
   AND k.index1 = u.index1

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON k.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'

    AND u.keberadaan_usaha_value IN ('1', '2');
