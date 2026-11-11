-- ======================================================================
-- RAW tgr_fd68e454.se2026_nested - BAGIAN 04/13
-- KABUPATEN BULUNGAN 6502 | SQL Lab StarRocks | Maks. 25 kolom
-- Grain tabel asal (jangan deduplikasi); kolom join: assignment_id, assignment_date_modified, assignment_id_timestamp, index1
-- ======================================================================

SELECT
    t.`assignment_id`,
    t.`assignment_date_modified`,
    t.`assignment_id_timestamp`,
    t.`index1`,
    t.`produk_sendiri_value`,
    t.`layanan_mamin_label`,
    t.`layanan_mamin_value`,
    t.`keg_penjualan_label`,
    t.`keg_penjualan_value`,
    t.`keg_jasa_label`,
    t.`keg_jasa_value`,
    t.`lokasi_usaha_label`,
    t.`lokasi_usaha_value`,
    t.`input`,
    t.`proses`,
    t.`produk`,
    t.`kbli_genai_label`,
    t.`kbli_genai_value`,
    t.`kbli_label`,
    t.`kbli_value`,
    t.`kategori`,
    t.`cek_kbli_pml_label`,
    t.`cek_kbli_pml_value`,
    t.`klasifikasi_label`,
    t.`klasifikasi_value`
FROM tgr_fd68e454.se2026_nested t
WHERE t.assignment_id IN (
    SELECT a.assignment_id
    FROM tgr_fd68e454.base_table_assignment a
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
  )
ORDER BY t.`assignment_id`, t.`assignment_date_modified`, t.`index1`;
