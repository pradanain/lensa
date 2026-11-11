-- ======================================================================
-- COUNT TABEL tcz_37526b20.pair_label_value_0
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Dipakai ulang untuk seluruh PART tabel yang sama.
-- ======================================================================

SELECT COUNT(*) AS jumlah_baris_presisi
FROM tcz_37526b20.pair_label_value_0 t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  );
