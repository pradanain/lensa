-- PENDUKUNG / TIDAK TERMASUK DALAM 3 QUERY MASTER
-- COUNT jumlah assignment aktif Kabupaten Bulungan, 1 baris per assignment
-- Jalankan sebelum menarik A / B / C. Max rows rekomendasi > total.
WITH ub_versi AS (
    SELECT r.assignment_id, r.keberadaan_label,
           ROW_NUMBER() OVER (
             PARTITION BY r.assignment_id
             ORDER BY r.assignment_date_modified DESC,
                      r.assignment_id_timestamp DESC
           ) AS urut_versi
    FROM tcz_37526b20.root_table r
    INNER JOIN tcz_37526b20.base_table_assignment a
      ON a.assignment_id = r.assignment_id
    WHERE a.is_active = 1 AND a.level_2_full_code = '6502'
)
SELECT COUNT(1) AS jumlah_baris_total,
       SUM(CASE WHEN REGEXP_REPLACE(r.keberadaan_label, '<[^>]*>', '')
                         LIKE '1.%' THEN 1 ELSE 0 END) AS jumlah_usaha_aktif
FROM tcz_37526b20.base_table_assignment a
INNER JOIN ub_versi r ON a.assignment_id = r.assignment_id
WHERE a.is_active = 1 AND a.level_2_full_code = '6502'
  AND r.urut_versi = 1;
