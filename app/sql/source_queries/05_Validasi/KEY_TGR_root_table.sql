WITH key_stats AS (
    SELECT t.`assignment_id`, t.`assignment_date_modified`, t.`assignment_id_timestamp`, COUNT(*) AS frekuensi
    FROM tgr_fd68e454.root_table t
    WHERE t.assignment_id IN (
        SELECT assignment_id
        FROM tgr_fd68e454.base_table_assignment
        WHERE is_active=1 AND level_2_full_code='6502'
    )
    GROUP BY t.`assignment_id`, t.`assignment_date_modified`, t.`assignment_id_timestamp`
)
SELECT
    COUNT(*) AS jumlah_key,
    SUM(frekuensi) AS total_baris,
    SUM(CASE WHEN frekuensi > 1 THEN 1 ELSE 0 END) AS key_berulang,
    SUM(CASE WHEN frekuensi > 1 THEN frekuensi-1 ELSE 0 END) AS baris_kelebihan
FROM key_stats;
