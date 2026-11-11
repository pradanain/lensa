-- ============================================================
-- REKONSILIASI UB: seluruh assignment vs kuesioner yang tersedia
-- Satu baris hasil; tidak mengaudit status atau EC
-- Kabupaten Bulungan 6502
-- ============================================================
WITH master AS (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
    GROUP BY a.assignment_id
),
root_ids AS (
    SELECT r.assignment_id
    FROM tcz_37526b20.root_table r
    INNER JOIN master m
        ON m.assignment_id = r.assignment_id
    GROUP BY r.assignment_id
)
SELECT
    COUNT(*) AS total_assignment_aktif,
    SUM(CASE WHEN r.assignment_id IS NOT NULL THEN 1 ELSE 0 END)
        AS ada_kuesioner_UB,
    SUM(CASE WHEN r.assignment_id IS NULL THEN 1 ELSE 0 END)
        AS tanpa_kuesioner_UB
FROM master m
LEFT JOIN root_ids r
    ON m.assignment_id = r.assignment_id;
