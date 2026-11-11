-- Local SQLite only; read-only validation.
PRAGMA integrity_check;
PRAGMA foreign_key_check;

SELECT source_id, SUM(raw_rows) AS raw_rows, SUM(clean_rows) AS clean_rows,
       SUM(raw_rows-clean_rows) AS deduplicated_rows
FROM imported_files GROUP BY source_id ORDER BY source_id;

SELECT source_id, COUNT(*) AS snapshot_count
FROM imported_files GROUP BY source_id ORDER BY source_id;

SELECT source_id, import_id FROM active_imports ORDER BY source_id;
