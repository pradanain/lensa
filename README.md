# LENSA SE2026

Eksplorasi dan Analisis SE2026 - BPS Kabupaten Bulungan.

Aplikasi FastAPI + React/TypeScript untuk direktori usaha UMKM/UB, keluarga/anggota, komposisi sektor, distribusi wilayah, pencarian KBLI 2025 dan ekspor Excel. Halaman Dashboard dan Raw Data sementara dibatasi dengan 403. Sensus dibaca dari SQLite existing; akun, cache, FTS dan audit memakai database aplikasi terpisah.

Menu Keluarga mengikuti pola Usaha: Ringkasan, Direktori dan Anggota, filter samping yang dapat ditutup, pencarian di atas data, ekspor sesuai filter, dan kartu pada ponsel. Ringkasan menampilkan jumlah serta distribusi keluarga/anggota secara terpisah per versi kuesioner. Rincian perumahan, pendidikan/pekerjaan dan aset dimuat saat dibuka. Form mempertahankan versi dan anggota terpilih, lalu mengembalikan pencarian, filter serta halaman daftar saat kembali. Maps keluarga memakai tagging keluarga pada versi tepat, dibuka hanya saat diklik dan mengikuti hak akses lokasi.

Komposisi sektor memakai diagram cincin jika seluruh nilai tersedia. Jika ada nilai yang ditahan, tampilan beralih ke grafik batang jumlah usaha, tanpa total atau persentase. Sektor yang ditahan tetap bertanda — dan tidak dianggap nol. Filter sumber/wilayah serta klik sektor tetap berlaku.

Direktori keluarga dan anggota mengikuti urutan Usaha: status Ditemukan/tinggal lebih dahulu, lalu Baru, kelengkapan kolom yang terlihat, dan nama menurut abjad dalam setiap status. Kode status keluarga dan anggota dipetakan terpisah. Urutan diterapkan sebelum pagination dan sama pada ekspor; informasi yang dibatasi hak akses tidak dipakai dalam peringkat.

Direktori keluarga menampilkan nomor bangunan di bawah nama KK tanpa ID singkat, SLS/SUB-SLS, alamat sesuai hak akses, jumlah anggota hasil pendataan, jumlah usaha ditemukan, Maps dan Form. Ditemukan berwarna hijau, Baru biru, status lain 3–6 kuning dan tidak ditemukan/asing abu-abu. Isian kosong tetap — dan nol tetap 0; pengayaan serta ekspor memakai versi keluarga tepat.

Detail kuesioner mengikuti pembaca PESSE: satu blok ditampilkan utuh tanpa pagination, dengan area isi yang dapat digulir. Daftar anggota/usaha berada di luar area gulir agar tidak menutup jawaban; pada ponsel memakai pilihan yang dapat dicari. Panel atas dan sidebar dapat disembunyikan untuk memperluas area baca. Tombol Sebelumnya/Berikutnya berpindah blok; pilihan versi tersedia pada Informasi sumber di sidebar.

Isi DTD menyesuaikan assignment keluarga atau BKU pada versi yang dipilih. Informasi usaha tetap tersedia untuk keduanya; blok anggota, pendidikan dan perumahan hanya tampil pada konteks keluarga. Nomor, penggunaan bangunan dan alamat membaca induk yang sesuai. Jika induknya belum dapat dipastikan, bagian terkait tetap tersedia dan jenis assignment ditandai belum pasti.

Identitas wilayah menampilkan lokasi dari master assignment dengan keterangan sumber; timestamp master tidak dianggap versi jawaban. Nama SLS memakai referensi lokal 2025_2 saat kode lengkap cocok. Isian perubahan wilayah dan identitas/kontak pemberi informasi yang tidak ikut diekspor dikelompokkan dalam rincian yang dapat dibuka.

Jawaban pilihan memakai label sumber atau pilihan statis template yang sesuai. Tiap isian memiliki pembatas dan pergantian nomor utama diberi garis lebih tegas. Jumlah/nominal memakai titik ribuan serta koma desimal; kode dan tahun tetap utuh. Tagging ditampilkan sesuai versi/roster yang dipilih, dengan tautan Maps yang dibuka saat diklik dan pembatasan akses yang sama dengan lokasi direktori.

Aturan tampil DTD mengikuti kondisi yang dapat dibuktikan dari template 7.1.2 dan jawaban pada versi/roster terpilih, termasuk cabang NIB, internet, umur, kepemilikan rumah serta ekonomi tahunan/bulanan. Isian yang terbukti tidak berlaku disembunyikan. Jika aturan atau data pengendalinya belum tersedia, isian kosong tetap dapat dibuka dalam rincian sesuai urutan form. Jawaban API tidak dihapus atau diubah. Tagging SE2026-P berada di bawah isian; catatan tahun/satuan tidak ditampilkan berulang pada jawaban.

Area baca form memakai lebar layar yang tersedia, dengan huruf lebih besar dan pembatas sejajar. Satu kontrol Cari bagian atau pertanyaan digunakan untuk berpindah blok atau menuju nomor/uraian tertentu, termasuk isian dalam rincian tertutup. Tombol Awal bagian mengembalikan posisi baca tanpa berpindah blok. Pilihan anggota/usaha yang sudah dibuka memakai cache memori sementara selama kunjungan yang sama; pilihan baru hanya memuat area jawaban. Cache dipisahkan berdasarkan assignment, versi dan pengguna/hak akses, lalu dibuang saat meninggalkan form atau berganti sesi. Modal tahunan DTD dan identitas pemberi jawaban dibedakan dari jawaban kosong bila kolomnya tidak disertakan dalam ekspor lokal. Modal saat usaha didirikan dan modal UB tetap menggunakan sumbernya masing-masing.

## Folder pengembangan

Folder ini menjadi tempat mengembangkan aplikasi. Buka folder ini di editor; jalankan Git, backend, frontend dan tes dari sini.

```text
Sensus Ekonomi 2026/
|-- lensa-se2026/       Kode aplikasi dan pengembangan aktif
|   |-- app/web/        UI React
|   |-- app/src/        API dan analitik Python
|   |-- app/config/     Registry, master dan mapping kuesioner
|   |-- app/sql/        Query aplikasi dan bukti sumber
|   |-- app/deploy/     Konfigurasi deployment
|   |-- app/tests/      Tes sintetis
|   |-- docs/           Panduan aplikasi
|   |-- .cache/         Virtualenv dan cache lokal
|   `-- .env            Path database lokal, tidak masuk Git
`-- Data/               Database, RAW, provenance dan arsip pengolahan
    |-- data/processed/se2026.sqlite
    |-- data/app/portal.sqlite
    |-- data/raw/
    `-- archive/
```

Pada komputer ini `.env` mengarahkan aplikasi ke database existing di folder `Data`, menggunakan path absolut. Database sensus dibaca saja; state akun/cache tetap terpisah. Tidak ada duplikasi database atau sinkronisasi dua salinan kode. Salinan kode lama di folder Data dipertahankan untuk pemulihan, dan pengembangan berikutnya dilakukan di folder ini.

Skrip pipeline, SQL historis, dan dua skrip kompatibilitas di `archive/project_history/scripts/` tetap tersedia untuk tes/provenance. Skrip tersebut bukan startup aplikasi. Pemeliharaan/sinkronisasi data tetap mengikuti workspace Data dan aturan validasinya.

## Production

Image amd64: `ghcr.io/pradanain/lensa:latest`, dengan tag immutable `sha-<commit>`.

**[Panduan deployment, persiapan akun, update dan rollback](docs/DEPLOYMENT.md)**

- Satu container menyajikan API dan frontend pada port internal 8000.
- Network Traefik existing: `cloudflared-net`; tidak ada port host yang dipublikasikan.
- Compose production: `app/deploy/compose.yml`; file `compose.yaml` root hanya untuk pengembangan.
- Login ditunda secara default, termasuk production. HTTPS, cookie Secure dan perlindungan CSRF tetap aktif; setup web ditutup. Akun existing dipertahankan.
- Workflow GitHub menguji source, membangun image, melakukan smoke test memakai data sintetis, lalu menerbitkan image SHA dan latest ke GHCR. Server hanya pull dan menjalankan image.
- Repository dan image tidak membawa dataset sensus, RAW, akun, password atau backup privat. Dataset dan state ditransfer secara privat ke server.

## Lokal

Klik `JALANKAN_PORTAL.cmd`, kemudian buka `http://127.0.0.1:8000/usaha`. Mode lokal tetap mendukung penggunaan tanpa login. Python 3.11+ dan Node 22.20+ dibutuhkan untuk instalasi/build pertama.

```powershell
python -m pip install --require-hashes -r app/requirements/dev.lock
cd app/web
npm ci
npm run build
cd ../..
python -B app/scripts/run_portal.py
```

Tanpa konfigurasi, lokasi default dataset privat adalah `data/processed/se2026.sqlite` dan state `data/app/portal.sqlite`. Pada workspace pengembangan terpisah ini, `.env` memakai lokasi existing di `../Data/data/`. Jangan menjalankan builder/sinkronisasi sebagai startup portal.

## Pengujian

```powershell
python -m pytest app/tests -q
cd app/web
npm run build
npm run lint
npm test
npm run test:e2e
```

Browser tests memakai database sintetis dan server test tersendiri. Kode pipeline historis yang diperlukan tes tetap dipertahankan; tidak menjadi alur startup. SQL sumber hanya evidence historis. Akses SQL Lab tidak diperlukan atau digunakan.

## Struktur source

| Lokasi | Isi |
|---|---|
| `app/src/se2026/web` | API, autentikasi, direktori, ekspor XLSX dan kuesioner |
| `app/src/se2026/analytics` | API agregat dengan grain, denominator dan supresi |
| `app/web` | UI React dan pengujian browser |
| `app/config`, `app/sql` | Registry metrik, master referensi dan evidence SQL |
| `app/deploy` | Dockerfile production, Compose dan script deploy |
| `.github/workflows` | Validasi dan build/publish GHCR |

Data privat dan laporan operasional lokal sengaja tidak dipublikasikan. Tidak ada deduplikasi berdasarkan nama; UB menggunakan assignment ID dan roster keluarga tetap mengikuti versi yang tepat.
