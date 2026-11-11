# Konfigurasi yang digunakan

- `analytics/metrics/`: registry 55 metrik; sumber definisi tunggal.
- `analytics/sources.json`: sumber semantik, grain dan whitelist dimensi.
- `analytics/dimensions/geography.json`: kebijakan kode wilayah.
- `analytics/dimensions/local_geography.json`: kamus lokal yang dihasilkan validator, terikat hash database.
- `analytics/numeric_fields.json`: kebijakan parsing, satuan dan periode field yang didukung.
- `sources.json`: mapping 27 sumber pipeline yang sudah diaudit; berbeda peran dari sumber semantik analytics.
- `incoming.json`: deklarasi file lokal berikutnya untuk dry-run/sinkronisasi.

Konfigurasi ini aktif; tidak perlu dibentuk ulang saat aplikasi dibuka. Pembentukan ulang registry merupakan pekerjaan pemeliharaan dan membutuhkan validasi ulang. Path data/asli di mapping tidak diubah dalam penataan proyek.
