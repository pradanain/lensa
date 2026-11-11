# LENSA SE2026 Kabupaten Bulungan

**Eksplorasi dan Analisis SE2026** - BPS Kabupaten Bulungan. [Standar penamaan](docs/app/APP_IDENTITY.md).

Portal eksplorasi SE2026 dengan fokus Usaha, direktori, komposisi sektor dan KBLI 2025. Menu Dashboard, Keluarga dan Raw Data sementara dibatasi dengan 403. Database sensus hanya dibaca; data responden tidak disertakan dalam repository atau image.

Klik **`JALANKAN_PORTAL.cmd`**, lalu buka **http://127.0.0.1:8000**. Aplikasi langsung terbuka tanpa login. Login disimpan untuk tahap berikutnya. [Panduan portal](docs/app/README.md) dan [hasil implementasi](docs/reports/app/IMPLEMENTATION_REPORT.md).

Untuk production: [panduan deployment](docs/DEPLOYMENT.md). Workflow GitHub membangun satu image `ghcr.io/pradanain/lensa` untuk amd64. Gunakan `app/deploy/compose.yml` pada network Traefik existing `cloudflared-net`. Mode production mewajibkan login, secure cookies, serta akun administrator yang disiapkan secara privat; setup web ditutup. Penggunaan lokal tanpa login tetap tersedia.

## Empat kelompok utama

| Folder | Isi | Dipakai untuk |
| --- | --- | --- |
| **`app/`** | Kode, konfigurasi, query, skrip dan tes | Menjalankan dan mengembangkan aplikasi |
| **`data/`** | Database aktif, RAW, incoming dan metadata | Data lokal serta provenance |
| **`docs/`** | Panduan, rancangan, referensi dan laporan per domain | Membaca dokumentasi dan bukti pengujian |
| **`archive/`** | Kode/query historis, paket dan backup | Penelusuran riwayat atau pemulihan |

Folder `SE2026_BULUNGAN_WORKSPACE/` dan dua berkas referensi ekspor di root adalah sumber asli yang dilindungi manifest; posisinya tetap dipertahankan. `.cache/` berisi cache pengembangan.

## Menjalankan

Gunakan Python 3.11+ dari folder ini:

```powershell
python app/scripts/analytics_query.py --list
python app/scripts/analytics_query.py --metric keluarga.count --group-by kecamatan
python app/scripts/analytics_query.py --metric usaha.internet_yes_rate
.cache/venv/Scripts/python.exe -B -m pytest -q --junitxml=docs/reports/app/python_tests.xml
```

Aplikasi menggunakan `se2026.analytics.Analytics` dari `app/src/`. Pipeline lokal tetap tersedia melalui `python main.py --help`. Audit, sinkronisasi dan builder registry tidak perlu dijalankan saat membuka aplikasi. Dependensi tes: `pytest` dan `openpyxl`; runtime CLI analitik memakai standard library. Runtime web memakai `app/requirements/web.lock`; tes lengkap memakai `dev.lock`. API/UI ada di `app/src/se2026/web/` dan `app/web/`.

- [Panduan portal dan akun lokal](docs/app/README.md)
- [Struktur dan peran setiap folder](docs/PROJECT_STRUCTURE.md)
- [API analitik](docs/analytics/ANALYTICAL_QUERY_API.md)
- [Registry metrik](docs/analytics/METRIC_REGISTRY.md)
- [Indeks laporan](docs/reports/README.md)
- [Roadmap dashboard](docs/analytics/ANALYTICAL_DEVELOPMENT_ROADMAP.md)

SQL Lab ditutup permanen. Seluruh pengembangan memakai data lokal, dengan UB berdasarkan assignment_id dan anggota TGR pada versi yang sama. Gunakan API agregat publik dengan denominator serta pengendalian sel kecil; data responden tidak diunggah ke layanan eksternal.
