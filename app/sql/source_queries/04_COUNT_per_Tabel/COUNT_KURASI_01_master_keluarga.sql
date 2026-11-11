-- COUNT PRESISI: mengikuti FROM/JOIN/WHERE query data, tanpa menghitung kolom SELECT.
SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.root_table r

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON r.assignment_id = a.assignment_id


WHERE
    /* ========================================================
       KABUPATEN BULUNGAN
       ======================================================== */
    a.level_2_full_code = '6502'

    /* ========================================================
       GOLDEN RULE:
       hanya assignment induk yang masih aktif
       ======================================================== */
    AND a.is_active = 1

    /* ========================================================
       FILTER KELUARGA

       ada_keluarga_value adalah jawaban aktual keberadaan
       keluarga, sekaligus membedakan assignment keluarga
       dengan BKU/usaha.
       ======================================================== */
    AND r.ada_keluarga_value IS NOT NULL;
