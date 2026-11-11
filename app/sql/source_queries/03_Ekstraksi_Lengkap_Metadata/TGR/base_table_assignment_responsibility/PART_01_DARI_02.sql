-- ======================================================================
-- RAW tgr_fd68e454.base_table_assignment_responsibility - BAGIAN 01/02
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, id
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`id`,
    t.`level_1_full_code`,
    t.`level_2_full_code`,
    t.`survey_user_before_id`,
    t.`survey_user_current_id`,
    t.`assignment_responsibility_status_id`,
    t.`date_created`,
    t.`is_active`,
    t.`before_user_id`,
    t.`before_survey_role_id`,
    t.`before_survey_role_name`,
    t.`before_survey_role_role_id`,
    t.`before_survey_role_can_pull_sample`,
    t.`before_survey_role_is_pencacah`,
    t.`before_survey_role_sequence`,
    t.`current_user_id`,
    t.`current_survey_role_id`,
    t.`current_survey_rolename`,
    t.`current_survey_rolerole_id`,
    t.`current_survey_role_can_pull_sample`,
    t.`current_survey_role_is_pencacah`,
    t.`current_survey_role_sequence`
FROM tgr_fd68e454.base_table_assignment_responsibility t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`;
