WITH tgr_aktif AS (
    SELECT assignment_id
    FROM tgr_fd68e454.base_table_assignment
    WHERE is_active=1 AND level_2_full_code='6502'
    GROUP BY assignment_id
),
root_ada AS (
    SELECT r.assignment_id
    FROM tgr_fd68e454.root_table r
    WHERE r.assignment_id IN (SELECT assignment_id FROM tgr_aktif)
    GROUP BY r.assignment_id
)
SELECT
    COUNT(*) AS total_assignment_tgr,
    SUM(CASE WHEN r.assignment_id IS NOT NULL THEN 1 ELSE 0 END) AS memiliki_root,
    SUM(CASE WHEN r.assignment_id IS NULL THEN 1 ELSE 0 END) AS tanpa_root
FROM tgr_aktif a
LEFT JOIN root_ada r ON a.assignment_id=r.assignment_id;
