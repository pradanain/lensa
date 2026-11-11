-- COUNT PRESISI UB TERBARU (satu record per assignment yang memiliki root)
WITH ub_versi AS (
    SELECT
        r.assignment_id,
        ROW_NUMBER() OVER (
            PARTITION BY r.assignment_id
            ORDER BY r.assignment_date_modified DESC,
                     r.assignment_id_timestamp DESC
        ) AS urut_versi
    FROM tcz_37526b20.root_table r
    INNER JOIN tcz_37526b20.base_table_assignment a
        ON r.assignment_id = a.assignment_id
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
)
SELECT COUNT(*) AS jumlah_baris_presisi
FROM ub_versi
WHERE urut_versi = 1;
