# LENSA SE2026

Eksplorasi dan Analisis SE2026 ? BPS Kabupaten Bulungan.

Aplikasi FastAPI + React/TypeScript untuk direktori usaha UMKM/UB, komposisi sektor, distribusi wilayah, pencarian KBLI 2025 dan ekspor Excel. Halaman Dashboard, Keluarga dan Raw Data sementara dibatasi dengan 403. Sensus dibaca dari SQLite existing; akun, cache, FTS dan audit memakai database aplikasi terpisah.

## Production

Image amd64: `ghcr.io/pradanain/lensa:latest`, dengan tag immutable `sha-<commit>`.

**[Panduan deployment, persiapan akun, update dan rollback](docs/DEPLOYMENT.md)**

- Satu container menyajikan API dan frontend pada port internal 8000.
- Network Traefik existing: `cloudflared-net`; tidak ada port host yang dipublikasikan.
- Compose production: `app/deploy/compose.yml`; file `compose.yaml` root hanya untuk pengembangan.
- Mode production mewajibkan autentikasi, cookie Secure, HTTPS origin dan akun admin privat. Setup web ditutup.
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

Lokasi default dataset privat: `data/processed/se2026.sqlite`; database aplikasi: `data/app/portal.sqlite`. Jangan menjalankan builder/sinkronisasi sebagai startup portal.

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
