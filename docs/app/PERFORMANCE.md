# Pemuatan data dan cache LENSA

Dashboard memuat angka Usaha, Keluarga, penggunaan internet dan distribusi wilayah secara mandiri. Bagian yang sudah siap langsung tampil. Catatan cakupan baru meminta angka ketika dibuka. Halaman tetap memakai metrik publik pada registry existing, dengan penahanan sel kecil yang sama.

Endpoint `/api/v1/analytics/summary` tetap tersedia untuk kompatibilitas. UI Dashboard memakai `/analytics/business-summary`, `/analytics/family-summary`, `/analytics/dashboard?part=internet`, dan `/analytics/query` untuk distribusi. Bagian catatan memakai `part=notes`; `part=counts` tersedia untuk konsumen yang memerlukan lima angka utama dalam satu respons.

## Saat aplikasi mulai

Jika `SE2026_BUILD_INDEX_ON_START=true`, aplikasi memeriksa cache direktori dan menyiapkan urutan Usaha/Keluarga/Anggota. Cache hasil tujuh metrik halaman awal juga diisi bila cache agregat aktif. Semua pembacaan sensus tetap read-only. Tidak ada ETL atau pembentukan baseline sensus pada startup.

Persiapan skor pertama setelah pembaruan ini membutuhkan waktu tambahan. Status siap baru diberikan setelah persiapan selesai; tunggu startup dan hindari menjalankan beberapa salinan launcher. Restart berikutnya menggunakan skor yang sudah tersimpan di database aplikasi. Jika sebuah metrik gagal validasi, pemanasan metrik dilewati dengan kode `ANALYTICS_WARMUP_SKIPPED`; API metrik tersebut tetap menolak hasil yang gagal validasi. Direktori lain tetap dapat digunakan.

## Lapisan cache

| Lapisan | Isi dan lokasi | Pembaruan |
| --- | --- | --- |
| Validasi analitik | Hasil pemeriksaan grain yang berhasil; memori proses terbatas | Identitas/stamp file sensus dan WAL serta definisi registry/SQL |
| Katalog geografi analitik | Label/kode wilayah; memori proses terbatas | Penanda snapshot yang sama |
| Hasil agregat | Respons API publik yang sudah disupresi; memori proses | Penanda snapshot, kebijakan supresi dan TTL existing |
| Urutan direktori | `status_rank`, `score_admin`, `score_viewer`; app DB existing | Snapshot direktori, referensi SLS/KBLI yang dimuat dan versi aturan urutan |
| Daftar pada browser | Halaman/filter yang sudah dibuka; memori sementara | Dipisahkan per pengguna/peran; stale 30 detik, dibuang 60 detik setelah tidak digunakan |

Cache validasi tidak menyimpan kegagalan dan tidak berbagi koneksi SQLite antar-thread. Hasil dari transaksi baca lama tidak boleh disimpan sebagai hasil snapshot baru. Pemeriksaan key/grain tetap dilakukan ketika sumber atau definisi berubah. Perubahan snapshot di tengah persiapan indeks/skor membatalkan transaksi cache dengan `DIRECTORY_SNAPSHOT_CHANGED`.

Skor admin dan Viewer memakai kolom yang terlihat pada masing-masing akses. Indeks urutan mempertahankan prioritas status, kelengkapan, nama `NOCASE` dan tie-breaker existing sebelum pagination. Rincian keluarga/usaha tetap diperkaya pada baris halaman terpilih dengan assignment, versi dan roster tepat. Cache baru hanya menambah kolom/indeks/metadata pada app DB; akun dan sensus tidak dimigrasi.

Referensi SLS tetap master 2025_2 yang dipilih. Perubahan file SLS dimuat ulang oleh direktori dan membatalkan penanda skor. Setelah perubahan master KBLI atau sinkronisasi snapshot resmi, restart aplikasi mengikuti alur pemeliharaan existing. Saat mengubah aturan skor pada kode, naikkan versi `order-v1` agar skor lama dihitung ulang.

## Pemuatan tampilan

Pustaka grafik dipisahkan dari komponen umum dan halaman analitik dimuat ketika dibuka. Direktori tidak memuat chunk grafik; judul KBLI dikirim bersama baris hasil dari referensi lokal. Katalog hierarki lengkap diminta saat filter KBLI dibuka atau filter KBLI sudah aktif dari tautan.

Halaman domain umum tetap tersedia langsung agar kembali dari form tidak tertunda oleh pengambilan kode halaman. Cache detail kuesioner tetap berlaku hanya selama kunjungan form dan dibuang ketika meninggalkan form. Logout, sesi kedaluwarsa dan perubahan akses tetap membersihkan state privat. Tidak ada penyimpanan responden pada localStorage, service worker, URL pencarian atau cache HTTP publik.

Pada ponsel, jarak antarbagian kartu diperkecil dan status omzet tidak diulang. Nominal nol, tidak tersedia, perlu diperiksa, estimasi bulanan ×12 dan nilai yang dibatasi tetap dibedakan. Logo utama tetap memakai aset existing; favicon memakai SVG kecil.

## Pemeriksaan setelah perubahan berikutnya

Jalankan tes analitik dan web, build/lint/unit frontend, serta pengujian browser sintetis. Periksa invalidasi cache, perubahan kebijakan supresi, akses admin/Viewer, urutan global dan ekspor, pengembalian konteks daftar serta pembersihan cache detail/sesi. Ukur dengan dataset lokal read-only dan app DB sementara; keluaran benchmark tidak boleh mencetak responden.

Bandingkan waktu saat cache kosong, hasil masih valid, dan sesudah restart. Laporkan biaya persiapan awal terpisah dari waktu permintaan. Uji beban sintetis tidak menjadi bukti kapasitas server produksi atau kecepatan jaringan pengguna.

Laporan penerapan dan bukti pengukuran disimpan lokal pada `docs/reports/app/PERFORMANCE_IMPLEMENTATION_2026-11-19.md` dan tidak termasuk paket source publik.
