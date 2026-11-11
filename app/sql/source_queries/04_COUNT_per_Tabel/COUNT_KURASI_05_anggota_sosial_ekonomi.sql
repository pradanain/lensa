-- COUNT PRESISI: mengikuti FROM/JOIN/WHERE query data, tanpa menghitung kolom SELECT.
SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.nested_dtsen_var v


/* ============================================================
   FILTER KELUARGA DITEMUKAN / BARU
   Root harus berasal dari versi questionnaire yang sama
   ============================================================ */

INNER JOIN tgr_fd68e454.root_table r
    ON v.assignment_id = r.assignment_id
   AND v.assignment_date_modified = r.assignment_date_modified


/* ============================================================
   ASSIGNMENT AKTIF
   ============================================================ */

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON v.assignment_id = a.assignment_id
   AND a.is_active = 1


WHERE

    /* Kabupaten Bulungan */
    a.level_2_full_code = '6502'

    /* Keluarga substantif */
    AND r.ada_keluarga_value IN ('1', '2');
