-- Local read-only relation. Each roster is aggregated BEFORE joining family.
-- Zero means no linked roster rows on this exact family-version, not a filled answer.
WITH member_counts AS (
    SELECT assignment_id,__version_normalized,COUNT(*) AS linked_member_rows
    FROM mart_anggota GROUP BY assignment_id,__version_normalized
), meter_counts AS (
    SELECT assignment_id,__version_normalized,COUNT(*) AS linked_meter_rows
    FROM mart_meteran GROUP BY assignment_id,__version_normalized
), business_counts AS (
    SELECT assignment_id,__version_normalized,COUNT(*) AS linked_business_rows
    FROM mart_usaha GROUP BY assignment_id,__version_normalized
)
SELECT f.assignment_id,f.__version_normalized,
       COALESCE(m.linked_member_rows,0) AS linked_member_rows,
       COALESCE(p.linked_meter_rows,0) AS linked_meter_rows,
       COALESCE(u.linked_business_rows,0) AS linked_business_rows
FROM mart_keluarga f
LEFT JOIN member_counts m ON f.assignment_id=m.assignment_id AND f.__version_normalized=m.__version_normalized
LEFT JOIN meter_counts p ON f.assignment_id=p.assignment_id AND f.__version_normalized=p.__version_normalized
LEFT JOIN business_counts u ON f.assignment_id=u.assignment_id AND f.__version_normalized=u.__version_normalized;
