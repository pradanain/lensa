-- Generated from the existing metric registry; local SQLite only.
-- Requires registered analytical UDFs, including TURNOVER_GROUP / TURNOVER_BASIS.
-- Internal validation only; application aggregates use Analytics.query with suppression.

-- metric_id: usaha_details.digital_usaha_coverage
-- bindings: [1]
SELECT COUNT(*) AS eligible_rows,COALESCE(SUM(CASE WHEN 1=1 AND e."has_digital_usaha"=? THEN 1 ELSE 0 END),0) AS numerator,COALESCE(SUM(CASE WHEN 1=1 THEN 1 ELSE 0 END),0) AS denominator FROM (SELECT t.*,TURNOVER_GROUP('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_group,TURNOVER_BASIS('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_basis FROM (SELECT "__version_normalized","assignment_id","index1","has_legalitas_usaha","has_kegiatan_usaha","has_digital_usaha","has_program_usaha","has_ekonomi_tahunan","has_ekonomi_bulanan","has_jaringan_usaha" FROM "mart_usaha_integrated" LIMIT -1 OFFSET 0) t LIMIT -1 OFFSET 0) e WHERE 1=1;

-- metric_id: usaha_details.ekonomi_bulanan_coverage
-- bindings: [1]
SELECT COUNT(*) AS eligible_rows,COALESCE(SUM(CASE WHEN 1=1 AND e."has_ekonomi_bulanan"=? THEN 1 ELSE 0 END),0) AS numerator,COALESCE(SUM(CASE WHEN 1=1 THEN 1 ELSE 0 END),0) AS denominator FROM (SELECT t.*,TURNOVER_GROUP('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_group,TURNOVER_BASIS('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_basis FROM (SELECT "__version_normalized","assignment_id","index1","has_legalitas_usaha","has_kegiatan_usaha","has_digital_usaha","has_program_usaha","has_ekonomi_tahunan","has_ekonomi_bulanan","has_jaringan_usaha" FROM "mart_usaha_integrated" LIMIT -1 OFFSET 0) t LIMIT -1 OFFSET 0) e WHERE 1=1;

-- metric_id: usaha_details.ekonomi_tahunan_coverage
-- bindings: [1]
SELECT COUNT(*) AS eligible_rows,COALESCE(SUM(CASE WHEN 1=1 AND e."has_ekonomi_tahunan"=? THEN 1 ELSE 0 END),0) AS numerator,COALESCE(SUM(CASE WHEN 1=1 THEN 1 ELSE 0 END),0) AS denominator FROM (SELECT t.*,TURNOVER_GROUP('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_group,TURNOVER_BASIS('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_basis FROM (SELECT "__version_normalized","assignment_id","index1","has_legalitas_usaha","has_kegiatan_usaha","has_digital_usaha","has_program_usaha","has_ekonomi_tahunan","has_ekonomi_bulanan","has_jaringan_usaha" FROM "mart_usaha_integrated" LIMIT -1 OFFSET 0) t LIMIT -1 OFFSET 0) e WHERE 1=1;

-- metric_id: usaha_details.jaringan_usaha_coverage
-- bindings: [1]
SELECT COUNT(*) AS eligible_rows,COALESCE(SUM(CASE WHEN 1=1 AND e."has_jaringan_usaha"=? THEN 1 ELSE 0 END),0) AS numerator,COALESCE(SUM(CASE WHEN 1=1 THEN 1 ELSE 0 END),0) AS denominator FROM (SELECT t.*,TURNOVER_GROUP('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_group,TURNOVER_BASIS('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_basis FROM (SELECT "__version_normalized","assignment_id","index1","has_legalitas_usaha","has_kegiatan_usaha","has_digital_usaha","has_program_usaha","has_ekonomi_tahunan","has_ekonomi_bulanan","has_jaringan_usaha" FROM "mart_usaha_integrated" LIMIT -1 OFFSET 0) t LIMIT -1 OFFSET 0) e WHERE 1=1;

-- metric_id: usaha_details.kegiatan_usaha_coverage
-- bindings: [1]
SELECT COUNT(*) AS eligible_rows,COALESCE(SUM(CASE WHEN 1=1 AND e."has_kegiatan_usaha"=? THEN 1 ELSE 0 END),0) AS numerator,COALESCE(SUM(CASE WHEN 1=1 THEN 1 ELSE 0 END),0) AS denominator FROM (SELECT t.*,TURNOVER_GROUP('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_group,TURNOVER_BASIS('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_basis FROM (SELECT "__version_normalized","assignment_id","index1","has_legalitas_usaha","has_kegiatan_usaha","has_digital_usaha","has_program_usaha","has_ekonomi_tahunan","has_ekonomi_bulanan","has_jaringan_usaha" FROM "mart_usaha_integrated" LIMIT -1 OFFSET 0) t LIMIT -1 OFFSET 0) e WHERE 1=1;

-- metric_id: usaha_details.legalitas_usaha_coverage
-- bindings: [1]
SELECT COUNT(*) AS eligible_rows,COALESCE(SUM(CASE WHEN 1=1 AND e."has_legalitas_usaha"=? THEN 1 ELSE 0 END),0) AS numerator,COALESCE(SUM(CASE WHEN 1=1 THEN 1 ELSE 0 END),0) AS denominator FROM (SELECT t.*,TURNOVER_GROUP('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_group,TURNOVER_BASIS('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_basis FROM (SELECT "__version_normalized","assignment_id","index1","has_legalitas_usaha","has_kegiatan_usaha","has_digital_usaha","has_program_usaha","has_ekonomi_tahunan","has_ekonomi_bulanan","has_jaringan_usaha" FROM "mart_usaha_integrated" LIMIT -1 OFFSET 0) t LIMIT -1 OFFSET 0) e WHERE 1=1;

-- metric_id: usaha_details.program_usaha_coverage
-- bindings: [1]
SELECT COUNT(*) AS eligible_rows,COALESCE(SUM(CASE WHEN 1=1 AND e."has_program_usaha"=? THEN 1 ELSE 0 END),0) AS numerator,COALESCE(SUM(CASE WHEN 1=1 THEN 1 ELSE 0 END),0) AS denominator FROM (SELECT t.*,TURNOVER_GROUP('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_group,TURNOVER_BASIS('TGR',t.assignment_id,t.__version_normalized,t.index1) AS turnover_basis FROM (SELECT "__version_normalized","assignment_id","index1","has_legalitas_usaha","has_kegiatan_usaha","has_digital_usaha","has_program_usaha","has_ekonomi_tahunan","has_ekonomi_bulanan","has_jaringan_usaha" FROM "mart_usaha_integrated" LIMIT -1 OFFSET 0) t LIMIT -1 OFFSET 0) e WHERE 1=1;
