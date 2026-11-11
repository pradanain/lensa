-- ======================================================================
-- COUNT TABEL tgr_fd68e454.base_table_assignment
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Dipakai ulang untuk seluruh PART tabel yang sama.
-- ======================================================================

SELECT COUNT(*) AS jumlah_baris_presisi
FROM tgr_fd68e454.base_table_assignment t
WHERE t.is_active = 1
  AND t.level_2_full_code = '6502';
