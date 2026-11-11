-- P1 SE2026 BULUNGAN | DTD / TGR | TABEL nested_dtsen_var
-- Variabel tambahan saja, bukan ekspor ulang P0.
-- 1 baris sumber = 1 anggota + versi (assignment_id, assignment_date_modified, index1)
-- Tiga kolom kunci tersebut WAJIB saat menggabungkan hasil dengan P0.
-- assignment_id_timestamp hanya atribut tambahan untuk pelacakan versi.
-- no_urut_kk_var adalah kolom bantu untuk pemeriksaan manual.
-- Cakupan sama secara substantif dengan P0: keluarga ditemukan/baru, assignment aktif kab. 6502.
-- Dedup kunci root_table pada CTE mencegah penggandaan karena versi root berulang.
-- Tidak melakukan SELECT wildcard atau COUNT(DISTINCT); tidak memakai PPL/PML.
-- Kolom _value/_label dibiarkan apa adanya, jangan ubah ke angka tanpa validasi.
-- FILE: 04_P1_ANGGOTA_PENYAKIT_KRONIS_B.sql | TOTAL KOLOM: 19 / 25

WITH root_keluarga AS (
    SELECT
        r.assignment_id,
        r.assignment_date_modified
    FROM tgr_fd68e454.root_table r
    WHERE r.ada_keluarga_value IN ('1','2')
    GROUP BY r.assignment_id, r.assignment_date_modified
)
SELECT
    v.`assignment_id`,
    v.`assignment_date_modified`,
    v.`assignment_id_timestamp`,
    v.`index1`,
    v.`no_urut_kk_var`,
    v.`sakit_hiv_value`,
    v.`sakit_hiv_label`,
    v.`sakit_kolestrol_value`,
    v.`sakit_kolestrol_label`,
    v.`sakit_sirosis_value`,
    v.`sakit_sirosis_label`,
    v.`sakit_talasemia_value`,
    v.`sakit_talasemia_label`,
    v.`sakit_leukemia_value`,
    v.`sakit_leukemia_label`,
    v.`sakit_alzheimer_value`,
    v.`sakit_alzheimer_label`,
    v.`sakit_lainnya_value`,
    v.`sakit_lainnya_label`
FROM tgr_fd68e454.nested_dtsen_var v
INNER JOIN root_keluarga r
    ON v.assignment_id = r.assignment_id
   AND v.assignment_date_modified = r.assignment_date_modified
WHERE v.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
)
ORDER BY v.assignment_id, v.assignment_date_modified, v.index1, v.assignment_id_timestamp;
