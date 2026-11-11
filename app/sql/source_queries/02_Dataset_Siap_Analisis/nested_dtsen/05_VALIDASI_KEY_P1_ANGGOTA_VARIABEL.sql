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
-- Hasil: jumlah kunci baris, total baris, key berulang, dan baris kelebihan.
-- Tidak menggunakan COUNT(DISTINCT); untuk menilai kemungkinan duplikat sumber.

WITH root_keluarga AS (
    SELECT
        r.assignment_id,
        r.assignment_date_modified
    FROM tgr_fd68e454.root_table r
    WHERE r.ada_keluarga_value IN ('1','2')
    GROUP BY r.assignment_id, r.assignment_date_modified
),
data_scope AS (
    SELECT v.assignment_id, v.assignment_date_modified, v.index1
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
), frekuensi_key AS (
    SELECT assignment_id, assignment_date_modified, index1,
           COUNT(*) AS frekuensi
    FROM data_scope
    GROUP BY assignment_id, assignment_date_modified, index1
)
SELECT
    COUNT(*) AS jumlah_kunci,
    COALESCE(SUM(frekuensi), 0) AS jumlah_baris,
    COALESCE(SUM(CASE WHEN frekuensi > 1 THEN 1 ELSE 0 END), 0) AS key_berulang,
    COALESCE(SUM(CASE WHEN frekuensi > 1 THEN frekuensi - 1 ELSE 0 END), 0) AS baris_kelebihan
FROM frekuensi_key;
