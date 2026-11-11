WITH key_stats AS (
    SELECT t.`assignment_id`, t.`assignment_date_modified`, t.`index1`, COUNT(*) AS frekuensi
    FROM tcz_37526b20.pusat_nested t
    WHERE t.assignment_id IN (
        SELECT assignment_id
        FROM tcz_37526b20.base_table_assignment
        WHERE is_active=1 AND level_2_full_code='6502'
    )
    GROUP BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`
)
SELECT
    COUNT(*) AS jumlah_key,
    SUM(frekuensi) AS total_baris,
    SUM(CASE WHEN frekuensi > 1 THEN 1 ELSE 0 END) AS key_berulang,
    SUM(CASE WHEN frekuensi > 1 THEN frekuensi-1 ELSE 0 END) AS baris_kelebihan
FROM key_stats;
