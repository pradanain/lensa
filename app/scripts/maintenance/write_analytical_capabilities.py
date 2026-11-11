"""Render the analytical plan from measured local coverage; no database access."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.layout import write_document
from se2026.common import dump,utcnow
from se2026.reporting import markdown_table

SOURCE_CONTEXT={
 'assignment_tgr':('Assignment operasional','Status assignment/kuesioner, asal listing, mode, done/external_done, waktu operasional, wilayah dan kelengkapan koordinat. Status ini tidak membuktikan audit final di sistem lain.'),
 'assignment_ub':('Assignment operasional UB','Denominator 226 assignment UB, status dan wilayah assignment; waktu operasional serta versi_root_terbaru hanya provenance.'),
 'keluarga':('Keluarga-versi','Keberadaan keluarga, ukuran keluarga, anggota listing/pendataan, bangunan dan indikasi jumlah usaha. Tidak semua record master memenuhi filter modul rincian.'),
 'perumahan':('Keluarga-versi','Jenis/kepemilikan/sewa bangunan; luas dan material/kondisi lantai-dinding-atap; sanitasi, air, penerangan, meteran serta belanja utilitas. Distribusi memakai denominator jawaban valid modul ini.'),
 'aset_keluarga':('Keluarga-versi','Pendapatan/pengeluaran keluarga bulanan; makanan mingguan dan nonmakanan bulanan/tahunan tetap dipisahkan; kepemilikan LPG, kulkas, AC, emas, perangkat, kendaraan, lahan dan rumah beserta nilai asetnya.'),
 'anggota':('Anggota-roster-versi','Umur, jenis kelamin, hubungan keluarga, keberadaan/domisili, perkawinan, kepemilikan usaha dan asal prelist. Nama/NIK/tanggal lahir rinci untuk tautan internal terbatas, bukan dimensi dashboard.'),
 'sosial_p0':('Anggota-roster-versi','Sekolah/ijazah, profesi/status pekerjaan, komponen dan total pendapatan pekerjaan, usaha/lainnya, serta rekening/dompet digital. Status kerja bukan definisi lengkap angkatan kerja resmi.'),
 'meteran':('Meteran-roster-versi','Daya dan jenis identitas PLN serta ketersediaan identitas. Banyak meteran per keluarga: agregasikan dahulu sebelum menggabungkan indikator keluarga; nomor pelanggan tidak menjadi indikator publik.'),
 'screening':('Keluarga-versi','Usaha prelist/ditemukan; indikasi kos, keliling, online, bongkar-pasang, konstruksi, usaha lain dan tujuh kelompok pertanian; jenis terindikasi serta cross-check. Screening adalah indikasi, bukan otomatis jumlah unit usaha terverifikasi.'),
 'bku':('BKU/root-versi','Keberadaan BKU, penggunaan bangunan, wilayah dan koordinat. Unit BKU berbeda dari unit usaha. Dua kolom keberadaan keluarga seluruhnya kosong pada modul ini.'),
 'usaha':('Usaha-roster-versi','Keberadaan, jenis/skala usaha, KBLI/kategori, kegiatan/produk, wilayah dan koordinat. Nama usaha bukan kunci identitas. SKALA/KBLI dapat kosong; gunakan denominator variabel yang diukur.'),
 'legalitas_usaha':('Usaha-roster-versi','Karakteristik penanggung jawab, NIB yang dilaporkan, badan usaha/koperasi, kawasan, laporan keuangan, kontak/website dan lokasi utama. NIB dilaporkan tidak sama dengan verifikasi registrasi legal eksternal.'),
 'kegiatan_usaha':('Usaha-roster-versi','Produksi/makan-minum/perdagangan/jasa, lokasi/input/proses/produk; KBLI GenAI/pilihan/prelist/akhir, kategori dan status perubahan. Bisa membandingkan klasifikasi lokal, bukan menjamin ketepatan KBLI secara substantif.'),
 'digital_usaha':('Usaha-roster-versi','Jaringan usaha, kantor pusat/cabang, penggunaan internet untuk pesanan/produksi/distribusi/pembelian/promosi serta teknologi digital; multi-respons tidak dijumlahkan sebagai unit usaha baru.'),
 'program_usaha':('Usaha-roster-versi','Lingkungan/budaya, halal/izin edar dan jumlah varian, kemitraan KDKMP/MBG, transaksi nonpenduduk, pekerja menurut jenis kelamin/status bayar, tahun operasi dan konsistensi pekerja.'),
 'ekonomi_tahunan':('Usaha-roster-versi, tahun referensi 2025','Gaji, biaya dan pendapatan utama/lainnya/total, aset tanah-bangunan/lainnya/total, persentase online, rentang aset, luas lahan dan flag konsistensi. Sumber memfilter operasi sebelum 2026; jangan campur dengan nilai bulanan.'),
 'ekonomi_bulanan':('Usaha-roster-versi, usaha mulai 2026','Biaya/pendapatan satu bulan terakhir, aset akhir bulan sebelumnya, persentase online, luas lahan dan komposisi modal awal. Bulan kalender tidak diekspor; jangan membuat tren bulanan atau mengalikan 12 secara otomatis.'),
 'jaringan_usaha':('Usaha-roster-versi, alias index_usaha=index1','Jenis jaringan, jumlah cabang/unit dilaporkan dan profil kantor pusat. Subset jaringan tertentu, bukan semua usaha.'),
 'kantor_unit':('Kantor/unit anak per usaha-versi','Jenis/lokasi kantor unit, lingkungan, pekerja, pengeluaran dan pendapatan 2025. Ada 26 baris anak; aset_unit_2025 seluruhnya kosong. Hindari menjumlahkan nilai unit bersama nilai induk tanpa aturan konsolidasi.'),
 'kantor_pusat':('BKU/root-versi berstatus keberadaan 7','Record root terkait data kantor pusat; bukan roster cabang dan bukan master identitas perusahaan pusat yang unik lintas assignment.'),
 'p1_pekerjaan':('Anggota-roster-versi','Profesi lain dan label pekerjaan/sumber pendapatan/rekening melengkapi P0. nilai_pend_pekerjaan adalah teks nonnumerik pada seluruh nilai terisi; tidak menjadi kolom uang siap-SUM.'),
 'p1_disabilitas':('Anggota-roster-versi','Enam dimensi fisik, mental, intelektual, netra, rungu, wicara dalam pasangan value/label. Hanya prevalensi jawaban teramati pada denominator valid; data sensitif, bukan diagnosis klinis.'),
 'p1_kronis_a':('Anggota-roster-versi','Hipertensi, rematik, asma, jantung, diabetes, TBC, stroke, kanker, hemofilia, ginjal: value/label. Analisis multi-kondisi hanya pada key-versi yang sama dan respons valid masing-masing.'),
 'p1_kronis_b':('Anggota-roster-versi','HIV, kolesterol, sirosis, talasemia, leukemia, Alzheimer dan lainnya: value/label. Jangan menamai seluruh anggota union sebagai orang unik lintas versi; batasi keluaran sel kecil.'),
 'ub_a':('Satu assignment UB','Profil/kegiatan/produk, KBLI/kategori, keberadaan, NIB/badan usaha, jaringan/pusat, wilayah jawaban dan penanggung jawab. id_penghubung terbukti assignment_id. Kode desa jawaban dapat berbeda dari master.'),
 'ub_b':('Satu assignment UB','Tahun operasi, pekerja, pendapatan/pengeluaran/aset, luas tanah dan komposisi modal. Ukuran keuangan terisi pada 117 dari 226 record; periode referensi rinci tidak tercantum pada nama/SQL lokal.'),
 'ub_c':('Satu assignment UB','Kawasan, cabang/pusat, NIB/halal/izin edar, internet dan teknologi, persentase online, lingkungan/budaya/KDKMP/MBG. Label dan angka persentase mempunyai denominator terisi sendiri.'),
}


def source_id_for_mart(name):
    return name.removeprefix('mart_')


def main(root=ROOT):
    a=json.loads((root/'docs/reports/readiness/analytical_readiness_audit.json').read_text(encoding='utf-8'))
    summaries={s['dataset']:s for s in a['sources']}
    variables=a['variables']
    docs=root/'docs'
    docs.mkdir(exist_ok=True)
    main_text=('# Kemampuan analitik SE2026 Bulungan berdasarkan baseline lokal\n\n'
        f'Audit baca pada {a["generated_utc"]}; database `{a["database"]}`. SQL Lab ditutup permanen. '
        'Seluruh kemampuan dan prioritas di bawah menggunakan dataset lokal yang benar-benar ada; tidak mensyaratkan COUNT baru, variabel tambahan atau pengambilan data dari sumber tersebut.\n\n'
        '## Ringkasan kesiapan\n\n'
        f'Tersedia {len(a["sources"])} dataset sumber dengan {sum(s["raw_rows"] for s in a["sources"]):,} baris RAW dan '
        f'{sum(s["clean_rows"] for s in a["sources"]):,} baris CLEAN, {len(variables)} kolom sumber (kemunculan dataset-kolom, bukan konsep unik), '
        f'{len(a["marts"])} mart dan tiga view alias CLEAN UB. {len(a["tables"])} tabel fisik mencakup RAW, CLEAN, provenance/kontrol dan link matched. '
        'Baris antarmodul tidak dijumlahkan sebagai jumlah penduduk/usaha: satu anggota muncul di beberapa modul dan 226 UB muncul pada master serta A/B/C.\n\n'
        'Analisis deskriptif wilayah, keluarga, anggota, BKU, profil usaha dan UB siap dikembangkan sekarang dengan denominator dan cakupan yang eksplisit. '
        'Keuangan yang format/satuannya belum jelas serta geografi berkode khusus memerlukan lapisan semantik lokal, bukan pengumpulan data baru. '
        'Empat kolom seluruhnya kosong tidak mendukung analisis nilainya; bukan hambatan bagi variabel lain.\n\n'
        '## Data tersedia, grain dan fungsi\n\n')
    main_text+=markdown_table(['Sumber CLEAN / mart sumber','RAW','CLEAN','Assignment unik','Grain / kunci','Fungsi dan batasan'],[
        [s['dataset'],s['raw_rows'],s['clean_rows'],s['distinct_assignments'],SOURCE_CONTEXT[s['dataset']][0]+' / '+', '.join(s['key']),SOURCE_CONTEXT[s['dataset']][1]] for s in a['sources']])+'\n\n'
    main_text+=('Seluruh dataset memiliki nol key invalid dan nol baris konflik pada baseline yang diaudit. '
                'Dalam tiap dataset sumber saat ini, jumlah unit tanpa versi sama dengan jumlah baris CLEAN: tidak ditemukan dua versi untuk key unit yang sama di dalam satu dataset. '
                'Ini tidak berarti versi sama antar-P0/P1; mart sosial mengandung union 139.918 key anggota-versi, termasuk 739 key P1-only. '
                'Tidak dilakukan deduplikasi lintas versi atau pencocokan nama/NIK.\n\n'
                'File Excel checklist, CSV manifest/peta query, ZIP yang sudah identik dengan hasil ekstraksi, backup SQLite, dan checkpoint ekspor lama bukan sampel responden tambahan. '
                'SQL yang tidak mempunyai file hasil hanya menjelaskan struktur historis, bukan variabel analitik tersedia. '
                'Semua sumber lokal yang dikonfigurasi sudah memiliki mart.\n\n'
                '## Seluruh mart dan cara menggunakannya\n\n')
    mart_notes={
        'mart_keluarga_integrated':('Keluarga-versi','Master keluarga LEFT JOIN perumahan, aset, screening; tidak membawa roster anggota/meteran/usaha secara lebar.'),
        'mart_usaha_integrated':('Usaha-roster-versi','Master usaha LEFT JOIN tujuh rincian one-to-one; kantor_unit tetap terpisah.'),
        'mart_sosial_p0_p1':('Union anggota-roster-versi','Full union key P0/P1; flag has_* menunjukkan irisan modul, bukan seluruh modul selalu terisi.'),
        'mart_sosial_p1_only':('Subset anggota-roster-versi','Diagnostik 739 key tanpa P0; bukan 739 orang baru.'),
        'mart_ub_integrated':('Assignment UB','226 master+A/B/C via assignment_id saja; ASSIGNMENT_KEY_VERIFIED, provenance QUESTIONNAIRE_VERSION_NOT_VERIFIED non-blocking.'),
        'mart_rekap_kecamatan':('Sistem × entitas × kode kecamatan','Ukuran jumlah_unit_versi; entitas tidak dijumlahkan bersama.'),
        'mart_rekap_desa':('Sistem × entitas × kode kecamatan/desa','Rekap kode assignment, bukan wilayah jawaban usaha.'),
        'mart_rekap_sls':('Sistem × entitas × kode kecamatan/desa/SLS/sub-SLS','Kode SLS dan sub-SLS dipertahankan sebagai komposit.'),
        'mart_rekap_wilayah':('Alias mart_rekap_sls','Keluaran sama dengan mart_rekap_sls; jangan menjumlahkan keduanya.'),
    }
    mart_rows=[]
    for m in a['marts']:
        sid=source_id_for_mart(m['mart'])
        grain,note=mart_notes.get(m['mart'],(SOURCE_CONTEXT.get(sid,('lihat skema',''))[0],'Proyeksi snapshot CLEAN aktif dengan provenance; variabel lengkap pada lampiran sumber.'))
        mart_rows.append([m['mart'],m['rows'],m['columns'],grain,note])
    main_text+=markdown_table(['Mart','Baris aktual','Kolom aktual','Grain','Penggunaan'],mart_rows)+'\n\n'
    main_text+=('View `clean_ub_a_standardized`, `clean_ub_b_standardized`, `clean_ub_c_standardized` mempertahankan id_penghubung dan menambah assignment_id; tidak mengubah tabel. '
                'Inventaris **setiap kolom pada seluruh 39 view**, termasuk kolom teknis/hasil integrasi, tersedia di '
                '[analytical_view_columns.csv](../metadata/analytical_view_columns.csv). Lampiran akhir dokumen ini memuat seluruh 609 kolom sumber, tipe, keterisian dan perannya.\n\n'
                '## Hubungan unit dan variabel\n\n'
                '```mermaid\nflowchart LR\n  A[Assignment TGR] --> F[Keluarga versi]\n  A --> B[BKU versi]\n  A --> U[Usaha roster versi]\n  F --> M[Anggota roster versi]\n  F --> E[Meteran roster versi]\n  M --> S[Sosial P0 dan P1 pada key versi sama]\n  U --> K[Kantor unit anak]\n  Z[Assignment UB] --> Q[UB A B C satu assignment]\n```\n\n'
                'Untuk TGR gunakan assignment_id + __version_normalized, ditambah index1 untuk anggota/usaha dan indeks kedua untuk kantor/unit. '
                'Atribut administratif master assignment boleh ditautkan melalui ID untuk geografi/status operasional karena master unik; ini bukan penggabungan jawaban anggota lintas versi. '
                'Untuk UB gunakan assignment_id saja. Timestamp dan batch bukan kondisi JOIN UB. '
                'Nomor urut, nama, NIK, alamat, nama bangunan dan KBLI tidak digunakan sebagai kunci unit.\n\n')
    main_text+=markdown_table(['Induk','Anak/modul','Baris anak','Matched versi/key','Unmatched','Kelebihan JOIN'],[
        [r[k] for k in ['parent','child','child_rows','matched_child_rows','unmatched_child_rows','multiplication_excess']] for r in a['relationship_coverage']])+'\n\n'
    main_text+=('Unmatched tetap dianalisis sebagai record modul mandiri dan masuk bucket cakupan yang sesuai. '
                'Tidak mengubah versi agar cocok. Perumahan/aset/screening di mart keluarga dan legalitas/digital/ekonomi di mart usaha berisi sedikit lebih sedikit record dibanding mart modul mandiri karena exact-key matching.\n\n')
    presence=[]
    for m in a['integrated_module_coverage']:
        for flag,count in m['module_presence'].items():
            presence.append([m['mart'],flag,count,m['rows'],f'{100*count/m["rows"]:.3f}%'])
    main_text+=markdown_table(['Mart induk','Penanda modul','Modul hadir','Baris induk/union','Cakupan'],presence)+'\n\n'
    b=a['business_assignment_links']
    main_text+=(f'Pada 53.647 usaha, exact assignment+versi menautkan {b["family_only"]:,} ke keluarga saja, '
                f'{b["bku_only"]:,} ke BKU saja, {b["both"]} ke keduanya, dan {b["neither"]} ke tidak satu pun. '
                'Karena itu, seluruh usaha tidak boleh disebut usaha keluarga atau dipaksakan menjadi anak keluarga. '
                'Hubungan yang didukung adalah berada pada assignment keluarga/BKU yang sama, bukan bukti kepemilikan orang tertentu. '
                'Anggota × usaha × meteran di bawah keluarga dapat membentuk produk kartesian; agregasikan masing-masing roster ke key keluarga-versi dahulu, kemudian JOIN hasil agregat one-to-one. '
                'Demikian pula kantor_unit harus dihitung/agregasikan per usaha-versi sebelum dikaitkan ke indikator induk; nilai induk dan cabang dapat overlap sehingga tidak dijumlahkan sebagai nilai konsolidasi tanpa aturan lokal.\n\n'
                '## Keterisian yang menentukan pilihan indikator\n\n')
    important=[('anggota','umur'),('anggota','kode_jenis_kelamin'),('sosial_p0','kode_ijazah_tertinggi'),('sosial_p0','kode_profesi_utama'),
               ('aset_keluarga','total_pendapatan_keluarga_sebulan'),('usaha','kbli'),('usaha','kategori'),('program_usaha','total_pekerja_jenis_kelamin'),
               ('ekonomi_tahunan','total_pendapatan_2025'),('ekonomi_tahunan','total_aset_2025'),('ekonomi_bulanan','total_pendapatan_bln'),
               ('ekonomi_bulanan','total_aset_bln'),('p1_pekerjaan','nilai_pend_pekerjaan'),('ub_b','total_pendapatan'),('p1_disabilitas','dis_fisik_value')]
    important_rows=[]
    for sid,col in important:
        v=next(v for v in variables if v['dataset']==sid and v['column']==col)
        important_rows.append([sid,col,v['sqlite_type'],v['nonempty_rows'],v['source_rows'],str(v['nonempty_percent'])+'%'])
    main_text+=markdown_table(['Dataset','Variabel','Tipe CLEAN','Terisi','Denominator modul','% terisi'],important_rows)+'\n\n'
    main_text+=('Terisi tidak sama dengan valid secara bisnis, tersedia tidak sama dengan berlaku untuk semua responden, dan NULL tidak dianggap nol/tidak. '
                'Status keberadaan dan skip pattern membedakan cakupan master dari modul. Gunakan value/label sesuai codebook lokal; jangan menetapkan sembarang angka 1 sebagai jawaban positif untuk semua field. '
                'Untuk indikator multi-respons, jumlah pilihan dapat melebihi jumlah unit.\n\n')
    main_text+=markdown_table(['Dataset','Irisan variabel pada record sama','Baris keduanya/semuanya terisi'],[
        [r['dataset'],', '.join(r['columns']),r['joint_nonempty_rows']] for r in a['joint_field_availability']])+'\n\n'
    main_text+=markdown_table(['Kolom kosong seluruhnya','Konsekuensi'],[
        [v['dataset']+'.'+v['column'],'Tidak ada analisis nilai untuk kolom ini; pertahankan NULL dan gunakan ukuran/kolom lokal lain yang tersedia.'] for v in variables if v['nonempty_rows']==0])+'\n\n'
    main_text+=('Seluruh 41.993 nilai terisi pada `p1_pekerjaan.nilai_pend_pekerjaan` masuk kategori teks nonnumerik pada pemeriksaan format; '
                'gunakan komponen/total pendapatan P0 dan label P1, jangan CAST teks tersebut menjadi uang. '
                '`ekonomi_bulanan.total_aset_bln` memiliki 483 skalar desimal, 1.321 teks berseparator dan 224 kosong: parsing locale lokal secara eksplisit perlu ditambahkan '
                'pada lapisan analitik tanpa mengubah nilai sumber. Jangan menjumlahkan subset 483 record lalu mengklaim total semua usaha baru. '
                'DECIMAL_TEXT mempertahankan presisi; gunakan Decimal untuk total uang. CAST AS REAL adalah pendekatan yang dapat membulatkan; SQLite CAST terhadap teks separator dapat menghasilkan angka parsial.\n\n'
                '## Analisis yang didukung\n\n')
    capabilities=[
        ['Operasional lokal','mart_assignment_tgr; mart_assignment_ub','status_assignment, kode_status_assignment, status_kuesioner, done, external_done, source_from, mode','Assignment','Jumlah/distribusi status, kelengkapan jawaban, prelist dan geografi','Baseline assignment masing-masing sistem; tidak mengasumsikan status sama dengan audit resmi di sistem lain.'],
        ['Keluarga dan keberadaan','mart_keluarga; mart_keluarga_integrated','keberadaan_keluarga, jumlah_anggota_listing, jumlah_anggota_hasil_pendataan, jumlah_keluarga_dalam_rumah','Keluarga-versi','Distribusi ukuran/keberadaan keluarga dan cross-check listing versus hasil','Pakai filter status yang dinyatakan; angka master bukan denominator semua pertanyaan rincian.'],
        ['Perumahan dan layanan dasar','mart_perumahan','jenis_bangunan, status_kepemilikan, luas_lantai, jenis/kondisi_lantai/dinding/atap, sanitasi, air, penerangan','Keluarga-versi','Distribusi kategori dan tabulasi silang kepemilikan × kondisi/utilitas/wilayah','NULL/skip terpisah; luas valid untuk ringkasan numerik setelah kontrol nilai.'],
        ['Ekonomi dan aset keluarga','mart_aset_keluarga','pendapatan/pengeluaran keluarga, belanja utilitas, LPG, emas, perangkat, kendaraan, lahan, rumah','Keluarga-versi','Median/kuantil/distribusi sumber lokal; kepemilikan aset; hubungan kondisi rumah–ekonomi pada key sama','Periode mingguan/bulanan/tahunan tidak dicampur; satuan uang dan komponen perlu ditampilkan. Bukan estimasi kemiskinan resmi.'],
        ['Demografi anggota','mart_anggota','umur, jenis_kelamin, hubungan_kepala_keluarga, status_perkawinan, keberadaan_anggota, kode_domisili','Anggota-roster-versi','Kelompok umur/jenis kelamin, komposisi keluarga, perkawinan dan domisili','Terapkan status keberadaan/domisili sesuai tujuan; nama/NIK bukan dimensi agregat.'],
        ['Pendidikan dan pekerjaan','mart_sosial_p0 + mart_anggota pada key sama','ijazah_tertinggi, partisipasi_sekolah, profesi_utama, kode_status_pekerjaan, umur, jenis_kelamin','Anggota-roster-versi','Tabulasi ijazah × profesi/status; perbandingan umur/jenis kelamin untuk irisan matched','Tidak memaksa 56 sosial P0 yang tidak matched ke anggota; tidak menamai indikator sebagai TPT/TPAK resmi.'],
        ['Pendapatan dan inklusi keuangan anggota','mart_sosial_p0; mart_p1_pekerjaan','pendapatan_gaji/tunjangan/honor/lembur/lainnya, total_pendapatan_*, rekening, label pendapatan','Anggota-roster-versi','Komposisi pendapatan, distribusi valid dan rekening/dompet digital','Denominator menurut status memiliki pendapatan dan jawaban valid; teks nilai_pend_pekerjaan bukan ukuran uang siap pakai.'],
        ['Disabilitas','mart_p1_disabilitas; irisan mart_sosial_p0_p1','dis_fisik/mental/intelek/netra/rungu/wicara_value dan _label','Anggota-roster-versi','Proporsi jawaban tiap dimensi; multi-dimensi pada record sama; silang pendidikan/pekerjaan bila matched','Hanya prevalensi laporan pada data lokal; denominator valid; hindari sel kecil dan identifikasi individu.'],
        ['Penyakit kronis','mart_p1_kronis_a/b; mart_sosial_p0_p1','Sepuluh kondisi A dan tujuh kondisi B dalam pasangan value/label','Anggota-roster-versi','Frekuensi/proporsi laporan kondisi dan ko-kejadian untuk key versi yang sama','Bukan diagnosis/kausalitas; irisan modul menentukan denominator; tidak menjumlahkan 4 modul sebagai orang unik.'],
        ['PLN','mart_meteran','daya_terpasang, jenis_identitas_pln, identitas_pln_tersedia, jumlah_meteran_keluarga','Meteran-roster-versi','Jumlah meteran, distribusi daya; agregat jumlah/daya per keluarga bila definisi tersedia','Meteran bukan keluarga. Nilai keluarga yang diulang setiap meteran tidak boleh dijumlahkan. ID pelanggan disembunyikan.'],
        ['Screening usaha keluarga','mart_screening','usaha_online/keliling/kos/pertanian, jumlah_jenis_usaha_terindikasi, jumlah_usaha_prelist/ditemukan, status_crosscheck','Keluarga-versi','Keluarga dengan indikasi per jenis; kecocokan prelist–ditemukan; potensi menurut wilayah','Indikasi berbeda dari roster usaha; satu keluarga dapat memiliki beberapa jenis.'],
        ['BKU/bangunan','mart_bku; mart_kantor_pusat','keberadaan_bku, penggunaan_bangunan, nomor_bangunan, kode_wilayah, koordinat, status_keberadaan','BKU/root-versi','Distribusi status/penggunaan dan konsentrasi assignment usaha per BKU','BKU bukan usaha; nomor bangunan tidak unik global; kolom keberadaan keluarga di BKU seluruhnya kosong.'],
        ['Profil usaha/UMKM','mart_usaha; mart_usaha_integrated','keberadaan_usaha, jenis_usaha, skala_usaha, kbli, kategori, kegiatan_utama, produk_utama','Usaha-roster-versi','Distribusi sektor/kategori/skala; lokasi dan keberadaan','Jangan menyebut semua 53.647 usaha sebagai usaha keluarga; KBLI/skala sebagian kosong.'],
        ['Legalitas dan pengusaha','mart_legalitas_usaha','punya_nib, badan_usaha, koperasi_kdkmp, mempunyai_laporan_keuangan, jenis_kelamin_pj, umur_pj, kawasan','Usaha-roster-versi','Formalitas yang dilaporkan; badan usaha/koperasi; profil pengusaha × sektor pada exact key','NIB bukan hasil verifikasi eksternal; kontak/NIK privat; denominator responden rincian.'],
        ['Kegiatan dan kualitas klasifikasi','mart_kegiatan_usaha','memproduksi_barang, layanan_makan_minum, penjualan_barang, aktivitas_jasa, kbli_genai/pilihan/prelist/akhir, kategori_final','Usaha-roster-versi','Komposisi kegiatan, perubahan dan ketersediaan KBLI, pemeriksaan konsistensi antarfield lokal','Perubahan pilihan bukan perubahan kegiatan ekonomi dalam waktu; tidak ada validasi eksternal kode.'],
        ['Digitalisasi dan jaringan','mart_digital_usaha; mart_jaringan_usaha','menggunakan_internet, internet_*; teknologi_digital, jaringan_usaha, jumlah_cabang, wilayah kantor pusat','Usaha-roster-versi','Adopsi/fungsi internet; teknologi × kategori/skala; jaringan dan lokasi pusat','Multi-respons; jaringan adalah subset; lokasi pusat bukan wilayah assignment usaha.'],
        ['Tenaga kerja dan program khusus','mart_program_usaha','pekerja_laki_laki/perempuan/dibayar/tidak_dibayar, total_pekerja_*, halal/BPOM, KDKMP/MBG, lingkungan/budaya','Usaha-roster-versi','Komposisi pekerja; konsistensi dua total; frekuensi program dan praktik','Jumlah pekerja bukan FTE; daftar kategori/program yang dilaporkan bukan penerima program terverifikasi.'],
        ['Ekonomi usaha 2025','mart_ekonomi_tahunan','total_pendapatan_2025, total_pengeluaran_2025, total_aset_2025, komponen biaya/pendapatan/aset, persen_online','Usaha-roster-versi/periode 2025','Distribusi/kuantil/total dalam unit sumber; selisih pendapatan–pengeluaran dan intensitas online','Selisih deskriptif bukan laba akuntansi/PDRB; cek flag konsistensi, satuan, nol, nilai ekstrem dan denominator.'],
        ['Ekonomi usaha mulai 2026','mart_ekonomi_bulanan','total_pendapatan_bln, total_pengeluaran_bln, modal_*_persen, aset*_bln','Usaha-roster-versi/periode bulanan sumber','Distribusi biaya/pendapatan sebulan; komposisi modal; aset setelah parsing lokal','Aset total berformat campuran; kode_rentang_aset_bln kosong. Tanpa bulan kalender, bukan time series.'],
        ['Kantor/unit anak','mart_kantor_unit','kode_jenis_unit, wilayah_unit, jumlah_pekerja_unit_2025, pengeluaran_unit_2025, pendapatan_unit_2025','Kantor-unit per usaha-versi','Jumlah/jenis/lokasi unit; statistik unit dan agregat anak terpisah','26 record kecil; aset tidak tersedia. Jangan menghitung kembali pekerja/pendapatan yang sudah termasuk induk.'],
        ['UB lengkap berdasarkan assignment','mart_ub_integrated','Profil/KBLI/keberadaan, pekerja, pendapatan/biaya/aset/modal, digitalisasi/lingkungan/program, status master','Assignment UB','Profil 226 UB; tabulasi sektor/operasional/digital; ringkasan keuangan 117 record valid','JOIN ID verified; versi historis hanya provenance. Keuangan tidak dianggap tersedia untuk 226. Wilayah master dan jawaban berbeda pada 136 record.'],
        ['Analisis lintas keluarga–usaha','Agregat mart_anggota/meteran/usaha + mart_keluarga pada versi sama','jumlah anggota/pekerja, indikasi usaha, sektor, ekonomi keluarga','Keluarga-versi setelah pre-aggregation','Hubungan deskriptif karakteristik keluarga dengan usaha dalam assignment yang sama','Bukan bukti orang tertentu pemilik usaha atau hubungan sebab-akibat; pisahkan usaha pada assignment BKU.'],
        ['Perbandingan TGR dan UB','Agregat terpisah mart_usaha dan mart_ub_integrated','kategori/KBLI, pekerja, digitalisasi dan ukuran ekonomi yang harmonis','Sistem × unit × wilayah/periode','Panel perbandingan cakupan dan distribusi masing-masing sumber','Tidak ada bridge identitas lintas sistem yang telah terbukti; jangan menjumlahkan/deduplikasi sebagai satu populasi usaha gabungan.'],
    ]
    main_text+=markdown_table(['Analisis','Tabel/mart','Variabel','Unit','Keluaran yang memungkinkan','Denominator/batasan'],capabilities)+'\n\n'
    main_text+=('Nama variabel yang diringkas dengan garis miring atau `*` pada tabel kemampuan adalah keluarga field, bukan query wildcard. '
                'Nama kolom persis tersedia lengkap pada lampiran. Median/kuantil dan tabulasi silang dapat dihitung lokal pada nilai valid; '
                'ketimpangan/konsentrasi hanya boleh disebut distribusi dalam baseline teramati, bukan estimasi wilayah yang sudah berbobot atau lengkap.\n\n'
                '## Agregasi kecamatan, desa, SLS dan sub-SLS\n\n'
                'Seluruh 27 mart sumber dapat ditautkan ke master assignment sistemnya tanpa orphan atau multiplication untuk atribut wilayah. '
                'Kolom kode tidak kosong pada seluruh record yang terhubung, tetapi keterisian bukan validasi makna wilayah. '
                'Baseline mengandung 234 assignment TGR dan 103 assignment UB dengan bagian kode kecamatan/desa di bawah 6502 seluruhnya nol. '
                'Pertahankan record tersebut dalam bucket kode khusus/belum teralokasi; tidak membuang atau mengarang kode. '
                'Kode jawaban UB berbeda dari kode desa master pada 136 dari 226 record; pilih definisi lokasi secara eksplisit, jangan menimpa satu dengan lainnya.\n\n')
    main_text+=markdown_table(['Sistem','Level','Kelompok kode terisi teramati'],[
        [r['system'],r['level'],r['observed_populated_code_groups']] for r in a['administrative_groups']])+'\n\n'
    main_text+=('Angka di atas adalah kelompok kode lokal, termasuk kode khusus, bukan daftar resmi kecamatan/desa/SLS. '
                'Rekap kecamatan 71 baris, desa 456 baris dan SLS/wilayah 5.037 baris juga memuat sistem dan entitas; bukan jumlah wilayah unik. '
                'Semua 28 pemeriksaan total rekap (4 view × 7 entitas) cocok dengan jumlah mart sumber masing-masing. '
                'mart_rekap_wilayah adalah alias hasil SLS; tidak dijumlahkan lagi.\n\n')
    geo_outputs=[
        ['Assignment/keluarga/BKU/usaha/UB','COUNT unit pada key grain, menurut status/kategori','Sistem + entitas + kode kecamatan/desa/SLS/sub-SLS','Tambah bucket kode khusus dan tampilkan denominator serta status keberadaan.'],
        ['Anggota/pendidikan/pekerjaan','Jumlah roster teramati, distribusi umur/jenis kelamin/ijazah/profesi','Wilayah assignment keluarga; exact version untuk jawaban silang','Jangan menamai hitungan union sebagai penduduk unik lintas waktu.'],
        ['Perumahan/aset/layanan','N jawaban valid, frekuensi kategori, median/kuantil numerik valid','Keluarga-versi + wilayah assignment','Perlu unit/periode konsisten; tidak menambahkan record tanpa modul.'],
        ['Usaha/tenaga kerja/digital','N usaha, N jawaban valid, jumlah pekerja menurut definisi, distribusi kategori','Usaha-versi + wilayah assignment','Agregat kantor anak terpisah dan persentase memakai denominator jawaban.'],
        ['UB','226 total; profil/kategori; keuangan pada subset terisi; unknown geography terpisah','Wilayah assignment master sebagai default yang dilabeli; wilayah jawaban sebagai alternatif terpisah','103 kode master bersufiks nol dan 136 perbedaan desa perlu terlihat pada kualitas geografi.'],
        ['Disabilitas/kronis','N respons valid, jumlah/proporsi laporan; irisan key sama untuk cross-tab','Utamakan kecamatan/desa; SLS hanya keluaran terbatas','Sel kecil dibatasi; NULL bukan tidak; tanpa detail orang/koordinat rumah.'],
    ]
    main_text+=markdown_table(['Domain','Agregasi','Dimensi wilayah','Kontrol'],geo_outputs)+'\n\n'
    main_text+=('Untuk subtotal gunakan numerator dan denominator mentah lalu hitung ulang persentase, bukan rata-rata persentase SLS/desa. '
                'Jumlahkan hanya entitas dan periode yang sama. Untuk SLS gunakan key komposit (sistem, kecamatan, desa, SLS, sub-SLS), bukan nama SLS saja. '
                'Peta choropleth tidak disiapkan sebagai kebutuhan awal karena file batas wilayah belum ada pada inventaris lokal; tabel/bar chart langsung memungkinkan. '
                'Koordinat lokal dapat mendukung ringkasan spasial setelah pemeriksaan rentang/ketepatan dan agregasi yang menjaga kerahasiaan, tanpa layanan geocoding luar.\n\n'
                '## Mart dan lapisan analitik yang perlu disempurnakan\n\n')
    refinements=[
        ['P0','Dimensi wilayah lokal dan bucket kode khusus','Kini kode terisi 100% tetapi terdapat kode nol dan konflik definisi UB','Bangun pemetaan di aplikasi/cache dari master lokal; simpan kode/label asli dan definisi lokasi. Tidak mengubah baseline.'],
        ['P0','Kamus metrik dan denominator per modul','Cakupan master vs rincian berbeda; has_* tersedia','Spesifikasi numerator, denominator, unit, filter, periode, sumber dan flag missing; JSON/config atau query SELECT lokal.'],
        ['P1','Proyeksi anggota + sosial P0/P1 exact-version','mart_sosial_p0_p1 belum membawa umur/jenis kelamin dari anggota','LEFT JOIN/union view aplikasi dengan explicit key; pertahankan unmatched, flag provenance dan grain anggota-versi; jangan latest-fill lintas versi.'],
        ['P1','Agregat keluarga–anggota/meteran/usaha serta BKU–usaha','Tidak ada mart agregat roster yang aman untuk cross-domain','GROUP BY key induk-versi pada setiap anak, baru JOIN hasil agregat; flag count dan cakupan anak.'],
        ['P1','Lapisan ukuran ekonomi presisi','DECIMAL_TEXT; total_aset_bln campuran separator; P1 nilai nonnumerik','Parser Decimal lokal untuk field yang semantiknya jelas, flag parsing/unit/periode, kolom turunan terpisah; source tetap utuh.'],
        ['P1','Cache indikator wilayah','Rekap sekarang baru jumlah unit-versi tujuh entitas','Cache agregat lokal berisi N valid/N kosong, nilai ringkasan, source hash dan definisi metrik. Tidak membuat giant flat table.'],
        ['P2','Mart kesehatan terproteksi','Value/label lengkap tetapi sensitif dan beberapa key lintas modul berbeda','Irisan key sama, denominator valid, kontrol sel kecil dan drill-down terbatas; tanpa NIK/nama/lokasi rinci.'],
        ['P2','Lapisan perbandingan TGR/UB','Tidak ada bridge identitas lintas sistem dan periode UB rinci belum eksplisit','Panel berdampingan, label cakupan/periode, harmonisasi konsep yang memang didukung; tidak memaksakan populasi gabungan.'],
    ]
    main_text+=markdown_table(['Prioritas','Penyempurnaan','Bukti kebutuhan aktual','Cara memakai data lokal'],refinements)+'\n\n'
    main_text+=('Seluruh penyempurnaan di atas adalah rekomendasi berikutnya; audit ini tidak membuat/mengganti view, tidak menulis database, dan tidak rebuild ETL. '
                'Awali dengan SELECT dan lapisan semantik aplikasi; materialisasi baru dipertimbangkan bila kebutuhan/performa terukur membuktikannya perlu.\n\n'
                '## Keterbatasan yang harus tampil kepada pengguna\n\n'
                '1. Angka menggambarkan baseline lokal dan cakupan filter yang ada; EOF/COUNT historis tetap catatan, bukan target yang harus dicapai. Tidak ada pembobotan atau universe referensi resmi terverifikasi yang dapat dipakai untuk klaim estimasi populasi resmi.\n'
                '2. NULL, record tidak mempunyai modul, skip pattern, kategori tidak diketahui dan angka nol adalah keadaan berbeda. Persentase selalu menyertakan N valid dan populasi modul.\n'
                '3. Key anggota/roster berbeda versi dipertahankan. Tidak tersedia panel longitudinal individu yang terbukti; perubahan timestamp bukan bukti perubahan kesejahteraan/penyakit.\n'
                '4. UB hanya satu record per assignment, JOIN verified. Versi historis tidak dinyatakan sama; perbedaan ini tidak memblokir analisis assignment.\n'
                '5. Periode referensi berbeda: ekonomi tahunan 2025, usaha mulai 2026 satu bulan terakhir/aset akhir bulan sebelumnya, keluarga mingguan/bulanan/tahunan. Periode rinci UB dan satuan mata uang tidak diasumsikan dari nama field. Jangan mencampur/annualisasi otomatis.\n'
                '6. Ukuran keuangan memerlukan tipe, satuan dan pemeriksaan konsistensi. Nilai ekstrem dipertahankan dan ditandai, tidak dihapus agar angka tampak cocok.\n'
                '7. Wilayah master assignment tidak selalu sama dengan wilayah jawaban/lokasi unit anak. Kode terisi dapat merupakan kode khusus; tampilkan unknown dengan jelas.\n'
                '8. TGR dan TCZ adalah sistem berbeda. Tanpa bridge identitas yang terbukti, perbandingan memakai panel terpisah, bukan deduplikasi nama atau penjumlahan populasi terpadu.\n'
                '9. NIK/KK, nama, kontak, identitas PLN, koordinat rinci, pendapatan serta kesehatan tetap lokal dan terbatas. Keluaran dashboard diprioritaskan agregat; sel kecil ditahan sesuai aturan produk.\n'
                '10. Data mendukung asosiasi deskriptif pada irisan yang tersedia, bukan klaim sebab-akibat, diagnosis medis, angka pengangguran/kemiskinan resmi, PDRB atau tren kalender tanpa struktur yang mendukungnya.\n\n'
                '## Bukti dan reproduksi\n\n'
                'Audit menggunakan mode=ro dan PRAGMA query_only=ON. SHA-256 database sebelum/sesudah identik. '
                'Tidak ada ekspor SQL Lab, sync, perubahan RAW/CLEAN atau migrasi database. Bukti agregat lengkap: '
                '[analytical_readiness_audit.json](../reports/analytical_readiness_audit.json), '
                '[cakupan relasi](../reports/analytical_relationship_coverage.csv), [cakupan wilayah](../reports/analytical_geographic_coverage.csv), '
                '[format ukuran teks](../reports/analytical_value_formats.csv). Reproduksi: `python app/scripts/maintenance/audit_analytical_readiness.py`, '
                '`python app/scripts/maintenance/profile_analytical_formats.py`, lalu `python app/scripts/maintenance/write_analytical_capabilities.py`.\n\n'
                '## Lampiran: seluruh variabel sumber aktual\n\n'
                'K=key, P=provenance, W=wilayah, Q=ukuran kuantitatif yang membutuhkan unit/periode, C=kategori/label/uraian, I=identitas/lokasi terbatas. '
                'Kolom key/provenance dipakai untuk tautan/audit, bukan dijumlahkan sebagai ukuran. Keterisian dihitung langsung pada CLEAN snapshot aktif. '
                'Semua field sumber tercantum; alias assignment_id UB dan seluruh kolom hasil MART/teknis ada pada CSV view.\n\n')
    roles={'KUNCI_UNIT_VERSI':'K','PROVENANCE':'P','WILAYAH':'W','UKURAN_KUANTITATIF_PERLU_UNIT':'Q',
           'KATEGORI_FLAG':'C','KATEGORI_LABEL_ATAU_URAIAN':'C','IDENTITAS_LOKASI_BUKAN_DIMENSI_PUBLIK':'I'}
    for s in a['sources']:
        sid=s['dataset']
        main_text+='### '+sid+'\n\n'
        main_text+=SOURCE_CONTEXT[sid][0]+'; '+str(s['clean_rows'])+' baris CLEAN. '+SOURCE_CONTEXT[sid][1]+'\n\n'
        rows=[]
        for v in variables:
            if v['dataset']!=sid:continue
            limit='kosong seluruhnya' if v['nonempty_rows']==0 else 'cakupan bersyarat' if v['nonempty_rows']<v['source_rows'] else 'terisi'
            if v['sensitivity']!='AGREGAT_INTERNAL':limit+='; terbatas'
            if (sid,v['column'])==('p1_pekerjaan','nilai_pend_pekerjaan'):limit+='; teks nonnumerik, bukan SUM'
            if (sid,v['column'])==('ekonomi_bulanan','total_aset_bln'):limit+='; parser separator lokal diperlukan'
            rows.append(['`'+v['column']+'`',v['sqlite_type'],v['nonempty_rows'],str(v['nonempty_percent'])+'%',roles[v['role']],limit])
        main_text+=markdown_table(['Variabel','Tipe SQLite','N terisi','% modul','Peran','Catatan'],rows)+'\n\n'
    write_document(root, 'docs/ANALYTICAL_CAPABILITIES.md', main_text)
    roadmap='''# Roadmap analitik dan dashboard lokal

SQL Lab ditutup permanen. Baseline adalah SQLite terintegrasi dan file lokal yang sudah ada. Rencana ini tidak bergantung pada data baru, konfirmasi COUNT sumber, atau variabel yang tidak tersedia. Audit hanya membaca database; item di bawah belum diimplementasikan sebagai perubahan MART/dashboard.

## Urutan prioritas berdasarkan manfaat, cakupan dan kesiapan

Skor 1–5 adalah penilaian rekayasa untuk pengurutan, bukan statistik kualitas: manfaat bagi pengguna, kecukupan data untuk indikator yang disebut, serta kesiapan implementasi lokal. Jumlah skor hanya alat prioritas; risiko kerahasiaan/perbedaan unit tetap menentukan urutan rilis.

'''
    priorities=[
        ['P0-1','Kamus metrik + baseline/cakupan','5','5','5','15','27 sumber, 609 kolom; 36 mart sudah tersedia','Spesifikasi grain, numerator/denominator, periode/unit, NULL/skip, sumber dan batasan untuk setiap KPI.'],
        ['P0-2','Dimensi wilayah dan unknown bucket lokal','5','4','4','13','234 TGR dan 103 UB berkode bawah-kabupaten nol; 136 perbedaan desa UB','Pilih wilayah assignment vs jawaban secara eksplisit; label geografi, bucket khusus dan rekonsiliasi jumlah tanpa membuang record.'],
        ['P1-1','Dashboard ringkasan cakupan dan kualitas','5','5','5','15','Hitungan tujuh entitas pada rekap cocok; semua sumber dapat ditautkan ke master','Kartu unit per sumber/grain, filter wilayah, modul terisi, unknown geografi, missing/skip; tidak menjumlahkan semua entitas.'],
        ['P1-2','Profil usaha/UMKM dan operasional UB','5','4','5','14','53.647 usaha; rincian sekitar 41.162; UB lengkap 226 assignment','Sektor/kategori/skala, keberadaan, formalitas dilaporkan, digital, pekerja; denominator dan panel TGR/UB terpisah.'],
        ['P1-3','Keluarga, perumahan dan demografi','5','4','5','14','62.621 keluarga, 142.593 anggota; perumahan 44.279 record','Distribusi keluarga/anggota, kondisi rumah dan aset; filter status/valid response; cross-tab memakai key versi sama.'],
        ['P1-4','Lapisan anggota–sosial dan agregat roster aman','5','4','4','13','139.179 P0; union 139.918 key; anggota–P0 matched 139.123','Proyeksi baca untuk umur/jenis kelamin × pendidikan/pekerjaan; agregat per induk sebelum cross-domain; unmatched dipertahankan.'],
        ['P1-5','Normalisasi ukuran ekonomi lokal','5','3','3','11','Aset bulanan: 1.321 teks separator; P1 nilai pendapatan 41.993 teks nonnumerik','Decimal dan parsing eksplisit untuk field yang didukung; provenance asli, flag parsing dan label satuan/periode. Tidak menulis balik RAW/CLEAN.'],
        ['P2-1','Dashboard ekonomi dan tenaga kerja','5','3','4','12','Tahunan 38.060, bulanan 2.028, keuangan UB 117 record terisi','Tab/distribusi tahunan dan bulanan terpisah; kuantil/surplus deskriptif/pekerja dengan denominator valid. Tidak ada annualisasi/total lintas periode otomatis.'],
        ['P2-2','Analisis keluarga–usaha dan BKU–usaha','4','3','3','10','40.709 usaha terkait keluarga, 12.555 BKU, 383 neither pada key versi sama','Agregasi roster per key induk-versi; tampilkan subset cakupan dan bukan kepemilikan individu/kausalitas.'],
        ['P2-3','Sosial/kesehatan terproteksi','4','4','3','11','P1 disabilitas/kronis sangat terisi, tetapi key antarwaktu tidak identik','Agregat label/value valid dan exact-version; sel kecil ditahan, NIK/nama/koordinat tidak masuk output umum.'],
        ['P3-1','Jaringan kantor/unit dan pola spasial lokal','3','2','3','8','Kantor anak 26; aset anak kosong; tidak ada file batas wilayah pada inventaris','Graf/tabel jaringan dan titik agregat bila valid; bukan kebutuhan peta poligon awal atau pencarian batas eksternal.'],
        ['Lintas fase','Cache/performa dan sinkronisasi file lokal','4','5','4','13','ETL idempoten dan provenance sudah tersedia','Cache agregat lokal setelah pengukuran query; file yang kemudian ditemukan lewat incoming/dry-run; tanpa asumsi sumber baru.'],
    ]
    roadmap+=markdown_table(['Prioritas','Fitur','Manfaat','Kecukupan','Implementasi','Skor','Bukti lokal','Hasil yang harus dicapai'],priorities)+'\n\n'
    roadmap+='''## Tahapan implementasi dan kriteria penerimaan

1. **Fondasi semantik.** Bentuk registry metrik dan geografi lokal di konfigurasi/query aplikasi. Setiap metrik mencantumkan sumber, key grain, definisi indikator, filter status, numerator, denominator, satuan/periode, aturan missing dan tingkat kerahasiaan. Kriteria: total agregat kembali ke jumlah source mart yang sama; bucket unknown ikut total; tidak ada persentase tanpa denominator.
2. **Dashboard deskriptif pertama.** Halaman Ringkasan, Wilayah, Keluarga/Anggota, Usaha/UMKM, UB, serta Kualitas/Cakupan. Penyaring sistem, entitas, wilayah, status dan periode hanya muncul bila benar-benar didukung. UB menampilkan 226 assignment lengkap dan catatan keuangan terisi 117, bukan menuntut timestamp.
3. **Relasi dan ukuran.** Tambah proyeksi anggota-sosial exact-version dan agregat anak per induk; parsing/Decimal untuk ukuran yang jelas. Kriteria: keunikan key dan no-row-multiplication; matched/unmatched tetap dihitung; kasus NULL/zero/skip dibedakan; separator tidak menyebabkan salah total; seluruh nilai sumber tetap tersedia.
4. **Analisis ekonomi dan sosial rinci.** Tambah tab keuangan per periode dan halaman sosial/kesehatan yang aksesnya dibatasi. Denominator dihitung setelah filter; persentase subtotal dihitung dari numerator/denominator, bukan rata-rata persentase. Label ukuran yang belum terverifikasi tetap eksplisit. Terapkan penahanan sel kecil dengan kebijakan lokal; usulan default produk k=5 dapat dikonfigurasi dan bukan klaim standar hukum/resmi.
5. **Performa dan pemeliharaan.** Ukur query aktual, tambahkan cache agregat lokal yang diikat pada hash/snapshot dan definisi metrik. Utamakan SELECT, temporary view koneksi atau cache terpisah. Materialisasi/migrasi database baseline hanya jika kebutuhan teknis terukur membuktikannya perlu; gunakan backup/transaksi/validasi yang ada. Sync mendukung file lokal yang tersedia/ditemukan kemudian, dengan schema, checksum dan jenis snapshot yang jelas.

## Rancangan interaksi dashboard

- Header menunjukkan baseline lokal, unit analisis, cakupan/filter, waktu observasi berkas dan catatan snapshot; tidak ada tombol atau instruksi pengambilan dari SQL Lab.
- Ringkasan memisahkan kartu assignment, keluarga, anggota, BKU, usaha, meteran dan UB. N modul terisi/valid selalu dapat dilihat. Hindari satu total yang menjumlahkan semua dataset.
- Drill-down wilayah bergerak kecamatan → desa → SLS/sub-SLS dengan key komposit serta bucket kode khusus. Untuk UB tersedia penjelasan wilayah master/jawaban, tanpa penggantian kode diam-diam.
- Halaman keluarga/anggota memisahkan keluarga dari roster. Hubungan pendidikan/pekerjaan memakai irisan exact-version; kesehatan tidak diisi dari versi lain.
- Halaman usaha memisahkan master semua status dari rincian ditemukan/baru; tab ekonomi 2025, usaha mulai 2026 dan UB mempunyai referensi/satuan sendiri. Status kelengkapan dan denominator tidak disembunyikan oleh chart.
- Unduhan agregat lokal menyertakan definisi metrik, sumber/grain, numerator/denominator dan catatan cakupan. Data individu tetap terbatas; tidak memakai upload, telemetry atau layanan debugging/geocoding luar untuk data responden.

## Yang tidak menjadi agenda pengembangan

Tidak ada ekspor tambahan SQL Lab, penyesuaian jumlah agar cocok COUNT historis, pengisian variabel yang tidak tersedia, deduplikasi bisnis berdasarkan nama, penggabungan anggota lintas versi, panel longitudinal/forecast tanpa data pendukung, estimasi resmi TPT/kemiskinan/PDRB, ataupun populasi usaha TGR+TCZ terpadu tanpa bridge identitas yang terbukti. Keterbatasan tersebut cukup dijelaskan dalam produk; analisis deskriptif yang didukung tetap berjalan.

Rujukan: [kemampuan dan seluruh variabel](ANALYTICAL_CAPABILITIES.md), [kebijakan baseline lokal](DATA_ACCESS_POLICY.md), dan [bukti audit](../reports/analytical_readiness_audit.json).
'''
    write_document(root, 'docs/ANALYTICAL_DEVELOPMENT_ROADMAP.md', roadmap)
    write_document(root, 'docs/DEVELOPMENT_ROADMAP.md', '# Roadmap pengembangan aktif\n\n'
        'SQL Lab ditutup permanen. Database terintegrasi adalah baseline pengolahan lokal; COUNT historis dan variabel yang tidak tersedia merupakan catatan cakupan non-blocking. '
        'RAW/CLEAN, provenance dan versi dipertahankan. Integrasi UB assignment_id telah tervalidasi untuk 226 assignment; anggota berbeda versi tidak digabungkan.\n\n'
        'Pekerjaan selesai: inventaris 27 sumber, 609 kolom sumber, audit seluruh 36 mart, keterisian, format ukuran teks, hubungan/grain dan geografi; '
        'dokumentasi kemampuan analitik lengkap. Database dan ETL tidak dibangun ulang.\n\n'
        'Prioritas: (1) kamus metrik dan dimensi wilayah/bucket khusus; (2) dashboard deskriptif cakupan, keluarga/anggota, usaha dan UB; '
        '(3) proyeksi anggota-sosial exact-version dan agregat roster; (4) parsing ukuran ekonomi lokal serta analisis per periode; '
        '(5) analisis sosial/kesehatan terproteksi dan cache berbasis kebutuhan terukur. Sinkronisasi hanya mengolah file lokal yang tersedia/ditemukan kemudian.\n\n'
        'Rencana rinci dan kriteria penerimaan: [roadmap analitik/dashboard](ANALYTICAL_DEVELOPMENT_ROADMAP.md). '
        'Variabel, sumber, grain dan batasan: [ANALYTICAL_CAPABILITIES.md](ANALYTICAL_CAPABILITIES.md).\n')
    proof=dict(generated_utc=utcnow(),sources_documented=len(summaries),source_columns_documented=len(variables),
               marts_documented=len(a['marts']),all_view_columns_catalogued=len(a['view_columns']),
               source_keys_complete=all(s['invalid_key_rows']==0 and s['conflict_rows']==0 for s in a['sources']),
               geography_no_multiplication=all(r['multiplication_excess']==0 for r in a['geography']),
               tested_relationships_no_multiplication=all(r['multiplication_excess']==0 for r in a['relationship_coverage']),
               regional_rollup_totals_agree=all(r['counts_agree'] for r in a['rekap_count_validation']),
               database_sha256=a['database_sha256'],database_unchanged=a['database_unchanged'],sql_lab_access=False,
               outputs=['docs/analytics/ANALYTICAL_CAPABILITIES.md','docs/analytics/ANALYTICAL_DEVELOPMENT_ROADMAP.md','docs/history/DEVELOPMENT_ROADMAP.md'])
    if not all(proof[k] for k in ['source_keys_complete','geography_no_multiplication','tested_relationships_no_multiplication','regional_rollup_totals_agree']):
        raise ValueError('ANALYTICAL_AUDIT_REQUIRES_QUALIFIED_DOCUMENTATION')
    dump(root/'docs/reports/readiness/analytical_documentation_validation.json',proof)
    print(json.dumps(proof,indent=2))


if __name__=='__main__':
    main()
