-- Narrow read-only social key/has_* projection; preserves exact normalized version.
-- UNION and indexed EXISTS prevent row multiplication and avoid SHA-order payload scans.
WITH keys AS (
SELECT assignment_id,__version_normalized,index1 FROM clean_sosial_p0 INDEXED BY ix_join_sosial_p0 WHERE __import_id=(SELECT import_id FROM active_imports WHERE source_id='sosial_p0') AND __key_valid=1 AND __conflict=0
UNION
SELECT assignment_id,__version_normalized,index1 FROM clean_p1_pekerjaan INDEXED BY ix_join_p1_pekerjaan WHERE __import_id=(SELECT import_id FROM active_imports WHERE source_id='p1_pekerjaan') AND __key_valid=1 AND __conflict=0
UNION
SELECT assignment_id,__version_normalized,index1 FROM clean_p1_disabilitas INDEXED BY ix_join_p1_disabilitas WHERE __import_id=(SELECT import_id FROM active_imports WHERE source_id='p1_disabilitas') AND __key_valid=1 AND __conflict=0
UNION
SELECT assignment_id,__version_normalized,index1 FROM clean_p1_kronis_a INDEXED BY ix_join_p1_kronis_a WHERE __import_id=(SELECT import_id FROM active_imports WHERE source_id='p1_kronis_a') AND __key_valid=1 AND __conflict=0
UNION
SELECT assignment_id,__version_normalized,index1 FROM clean_p1_kronis_b INDEXED BY ix_join_p1_kronis_b WHERE __import_id=(SELECT import_id FROM active_imports WHERE source_id='p1_kronis_b') AND __key_valid=1 AND __conflict=0
)
SELECT k.assignment_id,
       k.__version_normalized,
       k.index1,
       EXISTS(SELECT 1 FROM clean_sosial_p0 p INDEXED BY ix_join_sosial_p0 WHERE p.__import_id=(SELECT import_id FROM active_imports WHERE source_id='sosial_p0') AND p.assignment_id=k.assignment_id AND p.index1=k.index1 AND p.__version_normalized=k.__version_normalized AND p.__key_valid=1 AND p.__conflict=0) AS has_sosial_p0,
       EXISTS(SELECT 1 FROM clean_p1_pekerjaan p INDEXED BY ix_join_p1_pekerjaan WHERE p.__import_id=(SELECT import_id FROM active_imports WHERE source_id='p1_pekerjaan') AND p.assignment_id=k.assignment_id AND p.index1=k.index1 AND p.__version_normalized=k.__version_normalized AND p.__key_valid=1 AND p.__conflict=0) AS has_p1_pekerjaan,
       EXISTS(SELECT 1 FROM clean_p1_disabilitas p INDEXED BY ix_join_p1_disabilitas WHERE p.__import_id=(SELECT import_id FROM active_imports WHERE source_id='p1_disabilitas') AND p.assignment_id=k.assignment_id AND p.index1=k.index1 AND p.__version_normalized=k.__version_normalized AND p.__key_valid=1 AND p.__conflict=0) AS has_p1_disabilitas,
       EXISTS(SELECT 1 FROM clean_p1_kronis_a p INDEXED BY ix_join_p1_kronis_a WHERE p.__import_id=(SELECT import_id FROM active_imports WHERE source_id='p1_kronis_a') AND p.assignment_id=k.assignment_id AND p.index1=k.index1 AND p.__version_normalized=k.__version_normalized AND p.__key_valid=1 AND p.__conflict=0) AS has_p1_kronis_a,
       EXISTS(SELECT 1 FROM clean_p1_kronis_b p INDEXED BY ix_join_p1_kronis_b WHERE p.__import_id=(SELECT import_id FROM active_imports WHERE source_id='p1_kronis_b') AND p.assignment_id=k.assignment_id AND p.index1=k.index1 AND p.__version_normalized=k.__version_normalized AND p.__key_valid=1 AND p.__conflict=0) AS has_p1_kronis_b
FROM keys k;
