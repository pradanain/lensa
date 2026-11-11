WITH tgr AS (
  SELECT assignment_id
  FROM tgr_fd68e454.base_table_assignment
  WHERE is_active=1 AND level_2_full_code='6502'
  GROUP BY assignment_id
),
ub AS (
  SELECT assignment_id
  FROM tcz_37526b20.base_table_assignment
  WHERE is_active=1 AND level_2_full_code='6502'
  GROUP BY assignment_id
)
SELECT 'TGR' AS sumber, COUNT(*) AS total_assignment FROM tgr
UNION ALL
SELECT 'UB' AS sumber, COUNT(*) AS total_assignment FROM ub;
