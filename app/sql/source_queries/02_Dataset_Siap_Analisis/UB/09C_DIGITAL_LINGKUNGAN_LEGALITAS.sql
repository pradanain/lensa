-- =====================================================
-- MASTER USAHA BESAR (UB) SE2026 - KABUPATEN BULUNGAN
-- QUERY C: KARAKTERISTIK DAN DIGITALISASI USAHA
-- 25 KOLOM
-- =====================================================

WITH ub_versi AS (
    SELECT
        r.assignment_id,
        r.website,
        r.jenis_kawasan_label,
        r.nama_kawasan,
        r.nama_kek_ki_label,
        r.negara_kp_label,
        r.jml_kc,
        r.punya_nib_label,
        r.alasan_nib_label,
        r.internet_label,
        r.internet_pesanan_label,
        r.internet_produksi_label,
        r.internet_distribusi_label,
        r.internet_beli_label,
        r.internet_promosi_label,
        r.persen_online,
        r.digital_label,
        r.produk_sendiri_label,
        r.produksi_lingkungan_label,
        r.perlindungan_lingkungan_label,
        r.mitra_kdkmp_label,
        r.peran_mbg_label,
        r.sertifikat_halal_label,
        r.izin_edar_label,
        r.produk_seni_label,
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

    -- ===== KUNCI PENGHUBUNG =====
    -- 01. id_penghubung
    r.assignment_id AS id_penghubung,

    -- ===== STRUKTUR USAHA DAN KAWASAN =====
    -- 02. negara_kantor_pusat
    REGEXP_REPLACE(r.negara_kp_label, '<[^>]*>', '') AS negara_kantor_pusat,
    -- 03. jumlah_kantor_cabang
    r.jml_kc AS jumlah_kantor_cabang,
    -- 04. jenis_kawasan
    REGEXP_REPLACE(r.jenis_kawasan_label, '<[^>]*>', '') AS jenis_kawasan,
    -- 05. nama_kawasan
    r.nama_kawasan AS nama_kawasan,
    -- 06. nama_kek_ki
    REGEXP_REPLACE(r.nama_kek_ki_label, '<[^>]*>', '') AS nama_kek_ki,

    -- ===== LEGALITAS DAN SERTIFIKASI =====
    -- 07. memiliki_nib
    REGEXP_REPLACE(r.punya_nib_label, '<[^>]*>', '') AS memiliki_nib,
    -- 08. alasan_tanpa_nib
    REGEXP_REPLACE(r.alasan_nib_label, '<[^>]*>', '') AS alasan_tanpa_nib,
    -- 09. produk_bersertifikat_halal
    REGEXP_REPLACE(r.sertifikat_halal_label, '<[^>]*>', '') AS produk_bersertifikat_halal,
    -- 10. memiliki_izin_edar
    REGEXP_REPLACE(r.izin_edar_label, '<[^>]*>', '') AS memiliki_izin_edar,

    -- ===== INTERNET DAN TEKNOLOGI DIGITAL =====
    -- 11. website
    r.website AS website,
    -- 12. menggunakan_internet
    REGEXP_REPLACE(r.internet_label, '<[^>]*>', '') AS menggunakan_internet,
    -- 13. internet_pesanan
    REGEXP_REPLACE(r.internet_pesanan_label, '<[^>]*>', '') AS internet_pesanan,
    -- 14. internet_produksi
    REGEXP_REPLACE(r.internet_produksi_label, '<[^>]*>', '') AS internet_produksi,
    -- 15. internet_distribusi
    REGEXP_REPLACE(r.internet_distribusi_label, '<[^>]*>', '') AS internet_distribusi,
    -- 16. internet_pembelian
    REGEXP_REPLACE(r.internet_beli_label, '<[^>]*>', '') AS internet_pembelian,
    -- 17. internet_promosi
    REGEXP_REPLACE(r.internet_promosi_label, '<[^>]*>', '') AS internet_promosi,
    -- 18. persentase_pendapatan_online
    r.persen_online AS persentase_pendapatan_online,
    -- 19. memanfaatkan_teknologi_digital
    REGEXP_REPLACE(r.digital_label, '<[^>]*>', '') AS memanfaatkan_teknologi_digital,

    -- ===== PRODUK DAN LINGKUNGAN =====
    -- 20. produksi_barang_di_lokasi
    REGEXP_REPLACE(r.produk_sendiri_label, '<[^>]*>', '') AS produksi_barang_di_lokasi,
    -- 21. menghasilkan_produk_ramah_lingkungan
    REGEXP_REPLACE(r.produksi_lingkungan_label, '<[^>]*>', '') AS menghasilkan_produk_ramah_lingkungan,
    -- 22. perlindungan_lingkungan
    REGEXP_REPLACE(r.perlindungan_lingkungan_label, '<[^>]*>', '') AS perlindungan_lingkungan,
    -- 23. penggunaan_produk_seni_budaya
    REGEXP_REPLACE(r.produk_seni_label, '<[^>]*>', '') AS penggunaan_produk_seni_budaya,

    -- ===== KEMITRAAN DAN PROGRAM PEMERINTAH =====
    -- 24. kemitraan_kdkmp
    REGEXP_REPLACE(r.mitra_kdkmp_label, '<[^>]*>', '') AS kemitraan_kdkmp,
    -- 25. keterlibatan_mbg
    REGEXP_REPLACE(r.peran_mbg_label, '<[^>]*>', '') AS keterlibatan_mbg
FROM tcz_37526b20.base_table_assignment a
INNER JOIN ub_versi r ON a.assignment_id = r.assignment_id
WHERE a.is_active = 1
  AND a.level_2_full_code = '6502'
  AND r.urut_versi = 1
ORDER BY id_penghubung;
