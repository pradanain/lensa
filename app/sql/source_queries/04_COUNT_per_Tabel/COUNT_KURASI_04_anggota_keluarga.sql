-- COUNT PRESISI: mengikuti FROM/JOIN/WHERE query data, tanpa menghitung kolom SELECT.
SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.nested_dtsen d

INNER JOIN tgr_fd68e454.root_table r
    ON d.assignment_id = r.assignment_id
   AND d.assignment_date_modified = r.assignment_date_modified

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON d.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'
    AND r.ada_keluarga_value IN ('1', '2');
