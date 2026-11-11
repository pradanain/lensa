-- [DARI QUERY PENGGUNA] Skema dan filter asli dipertahankan; belum diuji langsung di SQL Lab.
-- ============================================================
-- [03_USAHA_KEGIATAN]
--
-- KEGIATAN DAN KLASIFIKASI KBLI USAHA SE2026
-- KABUPATEN BULUNGAN
--
-- UNIT DATA:
-- 1 baris = 1 usaha Ditemukan / Baru
--
-- KEY:
-- assignment_id
-- + assignment_date_modified
-- + index1
--
-- CAKUPAN:
-- keberadaan_usaha_value IN ('1','2')
--
-- JUMLAH KOLOM:
-- 25
--
-- CATATAN:
-- - Tidak mengambil PPL/PML
-- - Tidak mengulang wilayah/nama usaha dari MASTER
-- - KBLI akhir dipertahankan sebagai kode utama
-- - KBLI GenAI bukan KBLI final dan dapat memiliki prefix internal
-- - indikasi_sumber_kbli bersifat indikator, bukan bukti
--   proses finalisasi KBLI
-- ============================================================

SELECT

    /* ========================================================
       A. KEY USAHA
       ======================================================== */

    /* 01 */
    u.assignment_id,

    /* 02 */
    u.assignment_date_modified,

    /* 03 */
    u.index1,


    /* ========================================================
       B. KEGIATAN UTAMA
       ======================================================== */

    /* 04 */
    NULLIF(TRIM(u.keg_utama), '')
        AS kegiatan_utama,

    /* 05 */
    u.produk_sendiri_value
        AS memproduksi_barang,

    /* 06 */
    u.layanan_mamin_value
        AS layanan_makan_minum,

    /* 07 */
    u.keg_penjualan_value
        AS melakukan_penjualan_barang,

    /* 08 */
    u.keg_jasa_value
        AS aktivitas_jasa,

    /* 09 */
    u.lokasi_usaha_value
        AS lokasi_kegiatan_usaha,


    /* ========================================================
       C. INPUT - PROSES - PRODUK
       ======================================================== */

    /* 10 */
    NULLIF(TRIM(u.input), '')
        AS input_usaha,

    /* 11 */
    NULLIF(TRIM(u.proses), '')
        AS proses_usaha,

    /* 12 */
    NULLIF(TRIM(u.produk), '')
        AS produk_utama,


    /* ========================================================
       D. PENENTUAN KBLI
       ======================================================== */

    /* 13
       Nilai rekomendasi/hasil GenAI.

       Contoh:
       101262 -> KBLI 01262
       103110 -> KBLI 03110
       147302 -> KBLI 47302

       Jadi nilai ini TIDAK digunakan langsung
       sebagai KBLI final.
       ======================================================== */
    u.kbli_genai_value
        AS kbli_genai,

    /* 14 */
    NULLIF(TRIM(u.kbli_genai_label), '')
        AS kbli_genai_label,


    /* 15
       KBLI yang dipilih dari Master KBLI.
       Biasanya digunakan ketika rekomendasi tidak dipakai /
       kbli_genai = 999999.
       ======================================================== */
    NULLIF(TRIM(u.kbli_value), '')
        AS kbli_pilihan,

    /* 16 */
    NULLIF(TRIM(u.kbli_label), '')
        AS kbli_pilihan_label,


    /* 17 */
    NULLIF(TRIM(u.kategori), '')
        AS kategori_awal,


    /* ========================================================
       E. KBLI PRELIST & HASIL FINAL
       ======================================================== */

    /* 18 */
    NULLIF(TRIM(u.kbli_prelist), '')
        AS kbli_prelist,

    /* 19
       KBLI utama yang digunakan untuk analisis.
       Simpan sebagai TEXT agar leading zero tetap terjaga.
       ======================================================== */
    NULLIF(TRIM(u.kbli_akhir), '')
        AS kbli_akhir,

    /* 20 */
    NULLIF(TRIM(u.kategori_2025), '')
        AS kategori_2025,


    /* 21
       Kategori final.
       Prioritaskan kategori_2025,
       fallback ke kategori hasil pengisian.
       ======================================================== */
    COALESCE(
        NULLIF(TRIM(u.kategori_2025), ''),
        NULLIF(TRIM(u.kategori), '')
    ) AS kategori_final,


    /* ========================================================
       F. INDIKATOR SUMBER KBLI
       ======================================================== */

    /* 22
       BUKAN bukti workflow finalisasi.
       Hanya membaca field mana yang konsisten
       dengan KBLI akhir.

       MASTER_KBLI
         = kbli_value cocok dengan kbli_akhir

       GENAI_PRELIST_SAMA
         = hasil GenAI dan prelist sama-sama cocok
           dengan KBLI akhir

       GENAI
         = hasil GenAI cocok dengan KBLI akhir

       PRELIST
         = prelist dipertahankan sebagai KBLI akhir

       FINAL_LAINNYA
         = KBLI akhir tersedia tetapi tidak dapat dijelaskan
           dengan tiga sumber di atas
       ======================================================== */
    CASE

        WHEN NULLIF(TRIM(u.kbli_akhir), '') IS NULL
            THEN 'TIDAK_ADA_KBLI_AKHIR'


        /* Pilihan dari Master KBLI cocok dengan final */
        WHEN NULLIF(TRIM(u.kbli_value), '') IS NOT NULL
             AND TRIM(u.kbli_value) = TRIM(u.kbli_akhir)
            THEN 'MASTER_KBLI'


        /* GenAI dan prelist sama-sama cocok dengan final */
        WHEN NULLIF(TRIM(u.kbli_genai_value), '') IS NOT NULL
             AND TRIM(u.kbli_genai_value) <> '999999'

             AND RIGHT(
                    TRIM(u.kbli_genai_value),
                    5
                 ) = TRIM(u.kbli_akhir)

             AND NULLIF(TRIM(u.kbli_prelist), '') IS NOT NULL
             AND TRIM(u.kbli_prelist) = TRIM(u.kbli_akhir)

            THEN 'GENAI_PRELIST_SAMA'


        /* GenAI cocok dengan KBLI akhir */
        WHEN NULLIF(TRIM(u.kbli_genai_value), '') IS NOT NULL
             AND TRIM(u.kbli_genai_value) <> '999999'

             AND RIGHT(
                    TRIM(u.kbli_genai_value),
                    5
                 ) = TRIM(u.kbli_akhir)

            THEN 'GENAI'


        /* KBLI prelist dipertahankan */
        WHEN NULLIF(TRIM(u.kbli_prelist), '') IS NOT NULL
             AND TRIM(u.kbli_prelist) = TRIM(u.kbli_akhir)

            THEN 'PRELIST'


        ELSE 'FINAL_LAINNYA'

    END AS indikasi_sumber_kbli,


    /* ========================================================
       G. PERUBAHAN KBLI PRELIST -> FINAL
       ======================================================== */

    /* 23 */
    CASE

        WHEN NULLIF(TRIM(u.kbli_prelist), '') IS NULL
            THEN 'TANPA_PRELIST'

        WHEN NULLIF(TRIM(u.kbli_akhir), '') IS NULL
            THEN 'KBLI_AKHIR_KOSONG'

        WHEN TRIM(u.kbli_prelist) = TRIM(u.kbli_akhir)
            THEN 'TETAP'

        ELSE 'BERUBAH'

    END AS status_perubahan_kbli,


    /* ========================================================
       H. INDIKATOR KELENGKAPAN
       ======================================================== */

    /* 24
       1 = mempunyai KBLI akhir
       0 = KBLI akhir kosong
       ======================================================== */
    CASE
        WHEN NULLIF(TRIM(u.kbli_akhir), '') IS NOT NULL
            THEN 1
        ELSE 0
    END AS kbli_tersedia,


    /* 25
       Minimal mempunyai:
       - kegiatan utama
       - produk utama

       Digunakan untuk audit kelengkapan rincian kegiatan.
       ======================================================== */
    CASE
        WHEN NULLIF(TRIM(u.keg_utama), '') IS NOT NULL
             AND NULLIF(TRIM(u.produk), '') IS NOT NULL
            THEN 1
        ELSE 0
    END AS kegiatan_produk_tersedia


FROM tgr_fd68e454.se2026_nested u


/* ============================================================
   ASSIGNMENT AKTIF
   ============================================================ */

INNER JOIN tgr_fd68e454.base_table_assignment a
    ON u.assignment_id = a.assignment_id
   AND a.is_active = 1


WHERE

    /* Kabupaten Bulungan */
    a.level_2_full_code = '6502'

    /* Usaha substantif */
    AND u.keberadaan_usaha_value IN ('1', '2')


ORDER BY
    u.assignment_id,
    u.index1;
