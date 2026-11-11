-- ======================================================================
-- COUNT TABEL tgr_fd68e454.root_table
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Dipakai ulang untuk seluruh PART tabel yang sama.
-- ======================================================================

SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.root_table t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  );
