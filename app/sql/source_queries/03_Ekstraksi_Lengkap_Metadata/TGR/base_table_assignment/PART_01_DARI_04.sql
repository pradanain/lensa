-- ======================================================================
-- RAW tgr_fd68e454.base_table_assignment - BAGIAN 01/04
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`email`,
    t.`mode`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`is_active`,
    t.`approved_by_creator`,
    t.`assignment_error_status_type`,
    t.`assignment_id_timestamp`,
    t.`assignment_responsibility_admin`,
    t.`assignment_status_alias`,
    t.`assignment_status_id`,
    t.`code_identity`,
    t.`current_user_fullname`,
    t.`current_user_id`,
    t.`current_user_survey_role_can_pull_sample`,
    t.`current_user_survey_role_id`,
    t.`current_user_survey_role_is_pencacah`,
    t.`current_user_survey_role_name`,
    t.`current_user_username`,
    t.`data1`,
    t.`data10`,
    t.`data2`,
    t.`data3`
FROM tgr_fd68e454.base_table_assignment t
WHERE t.is_active = 1
  AND t.level_2_full_code = '6502'
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
