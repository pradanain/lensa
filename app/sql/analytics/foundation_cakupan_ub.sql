-- Generated from the existing metric registry; local SQLite only.
-- Requires registered analytical UDFs, including TURNOVER_GROUP / TURNOVER_BASIS.
-- Internal validation only; application aggregates use Analytics.query with suppression.

-- metric_id: ub.complete_module_coverage
-- bindings: [1, 1, 1, 1]
SELECT COUNT(*) AS eligible_rows,COALESCE(SUM(CASE WHEN 1=1 AND (e."has_assignment_ub"=? AND e."has_ub_a"=? AND e."has_ub_b"=? AND e."has_ub_c"=?) THEN 1 ELSE 0 END),0) AS numerator,COALESCE(SUM(CASE WHEN 1=1 THEN 1 ELSE 0 END),0) AS denominator FROM (SELECT t.*,TURNOVER_GROUP('TCZ',t.assignment_id,NULL,NULL) AS turnover_group,TURNOVER_BASIS('TCZ',t.assignment_id,NULL,NULL) AS turnover_basis FROM (SELECT "assignment_id","status_keberadaan","kbli_akhir","kategori_kbli","has_assignment_ub","has_ub_a","has_ub_b","has_ub_c" FROM "mart_ub_integrated" LIMIT -1 OFFSET 0) t LIMIT -1 OFFSET 0) e WHERE 1=1;
