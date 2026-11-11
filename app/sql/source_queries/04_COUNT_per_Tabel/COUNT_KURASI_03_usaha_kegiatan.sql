-- COUNT PRESISI: mengikuti FROM/JOIN/WHERE query data, tanpa menghitung kolom SELECT.
SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.se2026_nested u


/* ============================================================
   ASSIGNMENT AKTIF
   ============================================================ */

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON u.assignment_id = a.assignment_id
   AND a.is_active = 1


WHERE

    /* Kabupaten Bulungan */
    a.level_2_full_code = '6502'

    /* Usaha substantif */
    AND u.keberadaan_usaha_value IN ('1', '2');
