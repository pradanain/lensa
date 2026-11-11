-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- DATASET : 07_KELUARGA_SCREENING_USAHA_FINAL
--
-- DESKRIPSI:
-- Dataset hasil screening kegiatan usaha pada tingkat keluarga.
-- Menggabungkan jumlah usaha prelist, jumlah usaha hasil
-- pendataan, serta 13 indikator screening usaha keluarga.
--
-- TUJUAN:
-- 1. Mengidentifikasi indikasi kegiatan usaha keluarga.
-- 2. Membandingkan usaha prelist dengan hasil pendataan.
-- 3. Mendeteksi keluarga yang memiliki indikasi usaha tetapi
--    belum mempunyai usaha hasil pendataan.
-- 4. Mendeteksi usaha yang ditemukan walaupun screening tidak
--    menunjukkan indikasi usaha.
-- 5. Menjadi dataset audit/crosscheck dengan 01_USAHA_MASTER.
--
-- UNIT DATA:
-- 1 baris = 1 keluarga Ditemukan / Baru
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
--
-- FILTER:
-- Kabupaten Bulungan
-- Assignment aktif
-- Status keluarga Ditemukan / Baru
--
-- JUMLAH KOLOM:
-- 22 / 25
-- ============================================================

SELECT

    /* ========================================================
       A. KEY
       ======================================================== */

    /* 01 */
    r.assignment_id,

    /* 02 */
    r.assignment_date_modified,


    /* ========================================================
       B. JUMLAH USAHA
       ======================================================== */

    /* 03 */
    r.jumlah_usaha_prelist
        AS jumlah_usaha_prelist,

    /* 04 */
    r.jumlah_usaha_ditemukan
        AS jumlah_usaha_ditemukan,


    /* ========================================================
       C. SCREENING USAHA NONPERTANIAN
       1 = ada indikasi
       2 = tidak
       ======================================================== */

    /* 05 */
    r.usaha_kos_value
        AS usaha_kos_kontrakan,

    /* 06 */
    r.usaha_keliling_value
        AS usaha_keliling,

    /* 07 */
    r.usaha_online_value
        AS usaha_online,

    /* 08 */
    r.usaha_bongkar_value
        AS usaha_bongkar_pasang,

    /* 09 */
    r.usaha_konstruksi_value
        AS usaha_konstruksi_penggalian,

    /* 10 */
    r.usaha_lain_value
        AS usaha_lainnya,


    /* ========================================================
       D. SCREENING USAHA PERTANIAN
       ======================================================== */

    /* 11 */
    r.tanaman_pangan_value
        AS usaha_tanaman_pangan,

    /* 12 */
    r.hortikultura_value
        AS usaha_hortikultura,

    /* 13 */
    r.perkebunan_value
        AS usaha_perkebunan,

    /* 14 */
    r.peternakan_value
        AS usaha_peternakan,

    /* 15 */
    r.kehutanan_value
        AS usaha_kehutanan,

    /* 16 */
    r.perikanan_value
        AS usaha_perikanan,

    /* 17 */
    r.jasa_pertanian_value
        AS usaha_jasa_pertanian,


    /* ========================================================
       E. KETERSEDIAAN SCREENING
       ======================================================== */

    /* 18 */
    CASE
        WHEN r.usaha_kos_value IS NULL
         AND r.usaha_keliling_value IS NULL
         AND r.usaha_online_value IS NULL
         AND r.usaha_bongkar_value IS NULL
         AND r.usaha_konstruksi_value IS NULL
         AND r.usaha_lain_value IS NULL
         AND r.tanaman_pangan_value IS NULL
         AND r.hortikultura_value IS NULL
         AND r.perkebunan_value IS NULL
         AND r.peternakan_value IS NULL
         AND r.kehutanan_value IS NULL
         AND r.perikanan_value IS NULL
         AND r.jasa_pertanian_value IS NULL
            THEN 0
        ELSE 1
    END AS screening_usaha_terisi,


    /* ========================================================
       F. JUMLAH JENIS USAHA YANG TERINDIKASI

       Menghitung berapa jenis screening yang berkode 1.
       Ini bukan jumlah unit usaha, melainkan jumlah JENIS
       kegiatan yang terindikasi.
       ======================================================== */

    /* 19 */
      CASE WHEN TRIM(CAST(r.usaha_kos_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.usaha_keliling_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.usaha_online_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.usaha_bongkar_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.usaha_konstruksi_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.usaha_lain_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.tanaman_pangan_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.hortikultura_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.perkebunan_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.peternakan_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.kehutanan_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.perikanan_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
    + CASE WHEN TRIM(CAST(r.jasa_pertanian_value AS STRING)) = '1'
           THEN 1 ELSE 0 END
        AS jumlah_jenis_usaha_terindikasi,


    /* ========================================================
       G. ADA / TIDAK ADA INDIKASI USAHA
       ======================================================== */

    /* 20 */
    CASE
        WHEN TRIM(CAST(r.usaha_kos_value AS STRING)) = '1'
          OR TRIM(CAST(r.usaha_keliling_value AS STRING)) = '1'
          OR TRIM(CAST(r.usaha_online_value AS STRING)) = '1'
          OR TRIM(CAST(r.usaha_bongkar_value AS STRING)) = '1'
          OR TRIM(CAST(r.usaha_konstruksi_value AS STRING)) = '1'
          OR TRIM(CAST(r.usaha_lain_value AS STRING)) = '1'
          OR TRIM(CAST(r.tanaman_pangan_value AS STRING)) = '1'
          OR TRIM(CAST(r.hortikultura_value AS STRING)) = '1'
          OR TRIM(CAST(r.perkebunan_value AS STRING)) = '1'
          OR TRIM(CAST(r.peternakan_value AS STRING)) = '1'
          OR TRIM(CAST(r.kehutanan_value AS STRING)) = '1'
          OR TRIM(CAST(r.perikanan_value AS STRING)) = '1'
          OR TRIM(CAST(r.jasa_pertanian_value AS STRING)) = '1'
            THEN 1
        ELSE 0
    END AS ada_indikasi_usaha_screening,


    /* ========================================================
       H. SELISIH USAHA HASIL PENDATAAN VS PRELIST

       Positif  = hasil pendataan lebih banyak
       Nol      = sama
       Negatif  = hasil pendataan lebih sedikit

       NULL prelist dipertahankan sebagai NULL.
       ======================================================== */

    /* 21 */
    CASE
        WHEN r.jumlah_usaha_prelist IS NULL
          OR r.jumlah_usaha_ditemukan IS NULL
            THEN NULL

        ELSE
              CAST(r.jumlah_usaha_ditemukan AS INT)
            - CAST(r.jumlah_usaha_prelist AS INT)
    END AS selisih_usaha_ditemukan_prelist,


    /* ========================================================
       I. STATUS CROSSCHECK

       Digunakan untuk menentukan record yang perlu diperiksa.
       ======================================================== */

    /* 22 */
    CASE

        /* Ada jawaban YA dan ada usaha hasil pendataan */
        WHEN (
               TRIM(CAST(r.usaha_kos_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_keliling_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_online_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_bongkar_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_konstruksi_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_lain_value AS STRING)) = '1'
            OR TRIM(CAST(r.tanaman_pangan_value AS STRING)) = '1'
            OR TRIM(CAST(r.hortikultura_value AS STRING)) = '1'
            OR TRIM(CAST(r.perkebunan_value AS STRING)) = '1'
            OR TRIM(CAST(r.peternakan_value AS STRING)) = '1'
            OR TRIM(CAST(r.kehutanan_value AS STRING)) = '1'
            OR TRIM(CAST(r.perikanan_value AS STRING)) = '1'
            OR TRIM(CAST(r.jasa_pertanian_value AS STRING)) = '1'
        )
        AND COALESCE(CAST(r.jumlah_usaha_ditemukan AS INT), 0) > 0
            THEN 'KONSISTEN_ADA_USAHA'


        /* Ada indikasi screening tetapi roster usaha 0 */
        WHEN (
               TRIM(CAST(r.usaha_kos_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_keliling_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_online_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_bongkar_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_konstruksi_value AS STRING)) = '1'
            OR TRIM(CAST(r.usaha_lain_value AS STRING)) = '1'
            OR TRIM(CAST(r.tanaman_pangan_value AS STRING)) = '1'
            OR TRIM(CAST(r.hortikultura_value AS STRING)) = '1'
            OR TRIM(CAST(r.perkebunan_value AS STRING)) = '1'
            OR TRIM(CAST(r.peternakan_value AS STRING)) = '1'
            OR TRIM(CAST(r.kehutanan_value AS STRING)) = '1'
            OR TRIM(CAST(r.perikanan_value AS STRING)) = '1'
            OR TRIM(CAST(r.jasa_pertanian_value AS STRING)) = '1'
        )
        AND COALESCE(CAST(r.jumlah_usaha_ditemukan AS INT), 0) = 0
            THEN 'INDIKASI_ADA_TAPI_USAHA_0'


        /* Tidak ada indikasi YA tetapi roster usaha > 0 */
        WHEN COALESCE(CAST(r.jumlah_usaha_ditemukan AS INT), 0) > 0
            THEN 'USAHA_ADA_TANPA_INDIKASI'


        /* Screening seluruhnya tidak terisi */
        WHEN r.usaha_kos_value IS NULL
         AND r.usaha_keliling_value IS NULL
         AND r.usaha_online_value IS NULL
         AND r.usaha_bongkar_value IS NULL
         AND r.usaha_konstruksi_value IS NULL
         AND r.usaha_lain_value IS NULL
         AND r.tanaman_pangan_value IS NULL
         AND r.hortikultura_value IS NULL
         AND r.perkebunan_value IS NULL
         AND r.peternakan_value IS NULL
         AND r.kehutanan_value IS NULL
         AND r.perikanan_value IS NULL
         AND r.jasa_pertanian_value IS NULL
            THEN 'SCREENING_TIDAK_TERISI'


        ELSE 'KONSISTEN_TIDAK_ADA_USAHA'

    END AS status_crosscheck_screening_usaha


FROM tgr_fd68e454.root_table r

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON r.assignment_id = a.assignment_id
   AND a.is_active = 1

WHERE
    a.level_2_full_code = '6502'

    AND r.ada_keluarga_value IN ('1', '2')

ORDER BY
    r.assignment_id;
