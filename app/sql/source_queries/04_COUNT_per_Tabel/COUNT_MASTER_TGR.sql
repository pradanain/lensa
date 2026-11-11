WITH assignment_aktif AS (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1 AND a.level_2_full_code = '6502'
    GROUP BY a.assignment_id
)
SELECT COUNT(*) AS total_assignment_aktif
FROM assignment_aktif;
