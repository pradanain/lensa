-- COUNT PRESISI: mengikuti FROM/JOIN/WHERE query data, tanpa menghitung kolom SELECT.
SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.root_table r

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON r.assignment_id = a.assignment_id

WHERE
    a.level_2_full_code = '6502'
    AND a.is_active = 1

    -- Keluarga substantif
    AND r.ada_keluarga_value IN ('1', '2');
