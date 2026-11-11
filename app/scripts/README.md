# Perintah proyek

Jalankan dari root workspace. Untuk aplikasi/dashboard, gunakan `se2026.analytics.Analytics` dari `src/`; skrip adalah alat menjalankan query atau pemeliharaan.

## Dipakai sekarang

| File | Kapan dipakai | Efek |
| --- | --- | --- |
| `run_portal.py` | Menjalankan UI/API pada localhost:8000 | Sensus baca saja; akun/cache di app DB |
| `validate_portal.py` | Audit setelah perubahan portal | Memverifikasi SHA/manifest/UB; menulis bukti agregat dan cache app terpisah |
| `analytics_query.py` | Menampilkan daftar metrik atau membaca agregat lokal | SELECT saja; hasil ke terminal, dengan pengendalian sel kecil |
| `validate_analytical_foundation.py` | Setelah perubahan metrik atau sinkronisasi snapshot lokal | Database baca saja; memperbarui laporan validasi, kamus wilayah dan status registry |
| `document_analytical_foundation.py` | Setelah validasi/tes untuk memperbarui dokumentasi | Membaca bukti yang tersedia; menulis docs analytics dan SQL turunan per domain |

```powershell
python app/scripts/analytics_query.py --list
python app/scripts/analytics_query.py --metric keluarga.count --group-by kecamatan
python -m pytest -q --junitxml=docs/reports/analytics/full_suite.xml
```

Validator database nyata lebih berat daripada query tunggal. Tidak perlu dijalankan setiap membuka aplikasi. Renderer dokumentasi tidak menjalankan ulang query database.

## Pemeliharaan sesuai kebutuhan

| File | Fungsi | Perlu diperhatikan |
| --- | --- | --- |
| `maintenance/build_questionnaire_mapping.py` | Membentuk schema DTD/UB yang ditelaah | Menulis konfigurasi mapping, bukan sensus; bukan startup |
| `maintenance/build_analytical_registry.py` | Membentuk definisi registry dari schema lokal | Membentuk ulang konfigurasi; status metrik perlu divalidasi ulang. Bukan langkah startup |
| `maintenance/audit_analytical_readiness.py` | Mengukur cakupan variabel, relasi dan wilayah | SQLite baca saja, menulis laporan audit/katalog |
| `maintenance/profile_analytical_formats.py` | Memprofilkan bentuk angka/kode | SQLite baca saja, menulis laporan format |
| `maintenance/write_analytical_capabilities.py` | Merender katalog kemampuan dari audit | Memperbarui dokumen kemampuan; tidak membaca ulang database |

Urutan reproduksi audit kemampuan: `audit_analytical_readiness.py`, `profile_analytical_formats.py`, lalu `write_analytical_capabilities.py`, semuanya di `app/scripts/maintenance/`. Jalankan hanya ketika audit perlu diperbarui.

## Historis, tidak digunakan pada alur aktif

`archive/project_history/scripts/` dari root workspace berisi lima skrip fase awal: pemetaan workbook, wrapper audit lama, migrasi UB sekali pakai, pembaruan dokumen migrasi, dan rekonsiliasi blocker SQL Lab. Folder tersebut berada di luar app/. Entrypoint terminalnya tidak menjalankan operasi lama. Beberapa fungsi dipertahankan untuk pengujian regresi sintetis dan penelusuran keputusan terdahulu.

Jangan menjadikan skrip historis sebagai startup, tahapan ETL atau prasyarat UI. Migrasi UB sudah selesai dan SQL Lab ditutup permanen. Implementasi asli sebelum penataan tersimpan dalam backup penataan yang tercatat di `data/metadata/project_reorganization_mapping.json`.

Pipeline lokal tetap tersedia lewat `main.py` di root. Arti dan efek perintah pipeline dijelaskan pada [panduan struktur](../../docs/PROJECT_STRUCTURE.md).
