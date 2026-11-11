-- ======================================================================
-- RAW tcz_37526b20.pair_label_value_0 - BAGIAN 01/02
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, data_key, pair_label, pair_value
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`data_key`,
    t.`pair_label`,
    t.`pair_value`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`assignment_listing`,
    t.`assignment_status_alias`,
    t.`assignment_status_id`,
    t.`is_active`,
    t.`level_1_code`,
    t.`level_1_name`,
    t.`level_10_code`,
    t.`level_10_full_code`,
    t.`level_10_name`,
    t.`level_2_code`,
    t.`level_2_name`,
    t.`level_3_code`,
    t.`level_3_full_code`,
    t.`level_3_name`,
    t.`level_4_code`,
    t.`level_4_full_code`,
    t.`level_4_name`
FROM tcz_37526b20.pair_label_value_0 t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
