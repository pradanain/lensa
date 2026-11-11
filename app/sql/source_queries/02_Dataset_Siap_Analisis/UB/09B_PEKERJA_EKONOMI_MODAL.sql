-- =====================================================
-- MASTER USAHA BESAR (UB) SE2026 - KABUPATEN BULUNGAN
-- QUERY B: TENAGA KERJA, KEUANGAN, DAN PERMODALAN
-- 25 KOLOM
-- =====================================================

WITH ub_versi AS (
    SELECT
        r.assignment_id,
        r.tahun_operasi,
        r.tk_laki,
        r.tk_perempuan,
        r.tk_total,
        r.gaji,
        r.biaya_produksi,
        r.biaya_pembelian,
        r.operasional,
        r.non_operasional,
        r.total_pengeluaran,
        r.nilai_pendapatan,
        r.pendapatan_lain,
        r.total_pendapatan,
        r.aset_tanah,
        r.aset_non_tanah,
        r.aset_total,
        r.luas_tanah,
        r.milik_sendiri,
        r.non_profit,
        r.publik,
        r.non_publik,
        r.pemerintah,
        r.asing,
        r.lap_keuangan_label,
        ROW_NUMBER() OVER (
            PARTITION BY r.assignment_id
            ORDER BY r.assignment_date_modified DESC,
                     r.assignment_id_timestamp DESC
        ) AS urut_versi
    FROM tcz_37526b20.root_table r
    INNER JOIN tcz_37526b20.base_table_assignment a
        ON a.assignment_id = r.assignment_id
    WHERE a.is_active = 1
      AND a.level_2_full_code = '6502'
)

SELECT

    -- ===== DASAR OPERASI DAN TENAGA KERJA =====
    -- 01. id_penghubung
    r.assignment_id AS id_penghubung,
    -- 02. tahun_operasi
    r.tahun_operasi AS tahun_operasi,
    -- 03. pekerja_laki_laki
    r.tk_laki AS pekerja_laki_laki,
    -- 04. pekerja_perempuan
    r.tk_perempuan AS pekerja_perempuan,
    -- 05. jumlah_pekerja
    r.tk_total AS jumlah_pekerja,

    -- ===== PENDAPATAN USAHA =====
    -- 06. pendapatan_utama
    r.nilai_pendapatan AS pendapatan_utama,
    -- 07. pendapatan_lainnya
    r.pendapatan_lain AS pendapatan_lainnya,
    -- 08. total_pendapatan
    r.total_pendapatan AS total_pendapatan,

    -- ===== PENGELUARAN USAHA =====
    -- 09. gaji_dan_jaminan_sosial
    r.gaji AS gaji_dan_jaminan_sosial,
    -- 10. biaya_produksi
    r.biaya_produksi AS biaya_produksi,
    -- 11. biaya_pembelian_barang
    r.biaya_pembelian AS biaya_pembelian_barang,
    -- 12. biaya_operasional
    r.operasional AS biaya_operasional,
    -- 13. biaya_non_operasional
    r.non_operasional AS biaya_non_operasional,
    -- 14. total_pengeluaran
    r.total_pengeluaran AS total_pengeluaran,

    -- ===== ADMINISTRASI KEUANGAN =====
    -- 15. memiliki_catatan_keuangan
    REGEXP_REPLACE(r.lap_keuangan_label, '<[^>]*>', '') AS memiliki_catatan_keuangan,

    -- ===== ASET DAN LUAS TANAH =====
    -- 16. aset_tanah_bangunan
    r.aset_tanah AS aset_tanah_bangunan,
    -- 17. aset_selain_tanah_bangunan
    r.aset_non_tanah AS aset_selain_tanah_bangunan,
    -- 18. total_aset
    r.aset_total AS total_aset,
    -- 19. luas_tanah_m2
    r.luas_tanah AS luas_tanah_m2,

    -- ===== KOMPOSISI KEPEMILIKAN MODAL =====
    -- 20. modal_pribadi_persen
    r.milik_sendiri AS modal_pribadi_persen,
    -- 21. modal_nonprofit_persen
    r.non_profit AS modal_nonprofit_persen,
    -- 22. modal_korporasi_publik_persen
    r.publik AS modal_korporasi_publik_persen,
    -- 23. modal_korporasi_nonpublik_persen
    r.non_publik AS modal_korporasi_nonpublik_persen,
    -- 24. modal_pemerintah_persen
    r.pemerintah AS modal_pemerintah_persen,
    -- 25. modal_asing_persen
    r.asing AS modal_asing_persen
FROM tcz_37526b20.base_table_assignment a
INNER JOIN ub_versi r ON a.assignment_id = r.assignment_id
WHERE a.is_active = 1
  AND a.level_2_full_code = '6502'
  AND r.urut_versi = 1
ORDER BY id_penghubung;
