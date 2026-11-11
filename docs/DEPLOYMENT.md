# Deployment LENSA

Target: `https://lensa.pradanain.id`, Linux Mint amd64, repository `pradanain/lensa`.

## Arsitektur

Cloudflare Tunnel existing → Traefik existing (entrypoint `web`) → satu service `lensa:8000` melalui external network `cloudflared-net`. Frontend React dibangun di GitHub dan disajikan FastAPI. Tidak ada port host, Docker socket, database service baru, atau build di server.

Image: `ghcr.io/pradanain/lensa:latest` dan `ghcr.io/pradanain/lensa:sha-<commit-40-digit>`. Untuk deployment yang dapat diulang, gunakan tag SHA atau digest. Workflow `.github/workflows/docker-publish.yml` menjalankan tes Python/React/browser, build amd64, smoke test image dengan data sintetis, lalu publish SHA dan latest. Workflow hanya memublikasikan dari `main`.

## File server

```text
/srv/stacks/lensa/
  compose.yml
  .env
  deploy.sh
  .docker/                   # hanya jika GHCR membutuhkan login; mode 700
/storage/data/lensa/
  census/se2026.sqlite       # database sensus existing, mount read-only
  state/portal.sqlite        # akun, cache lokal, FTS dan audit; writable
  backups/                   # snapshot SQLite dan konfigurasi privat
```

Database, RAW, akun, password dan file privat tidak disertakan dalam repository, image, atau artifact GitHub. File sensus harus ditransfer langsung dari workspace tepercaya ke server melalui jalur privat. Jangan mengambil dataset dari repository/image.

## Persiapan pertama

Audit read-only server terlebih dahulu: hostname/arsitektur, Docker/Compose, kapasitas disk/RAM, service existing, dan network `cloudflared-net`. Jangan mengubah stack lain. Verifikasi subnet aktual dengan:

```bash
docker network inspect cloudflared-net --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

Buat direktori hanya bila belum ada, dan jangan menimpa konfigurasi/data existing:

```bash
sudo mkdir -p /srv/stacks/lensa /storage/data/lensa/{census,state,backups}
sudo chown "$USER:$USER" /srv/stacks/lensa
sudo chown 10001:10001 /storage/data/lensa/state /storage/data/lensa/backups
sudo chmod 700 /srv/stacks/lensa /storage/data/lensa/state /storage/data/lensa/backups
```

Salin `app/deploy/compose.yml`, `app/deploy/deploy.sh`, dan contoh `app/deploy/production.env.example` ke lokasi stack di atas (`production.env.example` menjadi `.env`). Isi `LENSA_TRUSTED_PROXIES` dengan subnet yang baru diverifikasi. Simpan `.env` dengan mode 600 dan `deploy.sh` dengan mode 700. Jangan memakai `compose.yaml` root untuk production; file itu adalah konfigurasi pengembangan lama.

Transfer `data/processed/se2026.sqlite` ke `/storage/data/lensa/census/se2026.sqlite`, periksa SHA-256 sama sebelum/sesudah, lalu beri akses baca UID 10001:

```bash
sudo chown root:10001 /storage/data/lensa/census/se2026.sqlite
sudo chmod 640 /storage/data/lensa/census/se2026.sqlite
```

Pastikan directory induk dapat dilalui UID 10001. Jangan mengubah permission direktori layanan lain.

## Akun production

Login ditunda sesuai keputusan pengguna. Default image dan Compose memakai `LENSA_AUTH_ENABLED=false`; halaman Usaha, direktori, detail dan ekspor dapat digunakan tanpa akun. Akun dan sesi existing tetap disimpan. Setup web tetap ditutup, HTTPS, secure cookies dan perlindungan CSRF tetap aktif. Tidak perlu bootstrap akun untuk penggunaan tanpa login.

Untuk mengaktifkan login kelak, tetapkan `LENSA_AUTH_ENABLED=true` pada `.env`. Hanya pada mode tersebut startup dan readiness mensyaratkan admin aktif. Bagian bootstrap berikut bersifat opsional untuk persiapan mode login.

Jika state production sudah memiliki akun, pertahankan file tersebut. Untuk state baru, provision satu admin secara interaktif di server sebelum menjalankan service (password tidak masuk argumen, log atau shell history):

```bash
cd /srv/stacks/lensa
docker pull ghcr.io/pradanain/lensa:latest
docker run --rm -it --network none --user 10001:10001 --read-only \
  --mount type=bind,src=/storage/data/lensa/state,dst=/srv/data/app \
  --entrypoint python ghcr.io/pradanain/lensa:latest \
  -m se2026.web.bootstrap --database /srv/data/app/portal.sqlite --username pradanain
```

Perintah menolak mengganti akun existing. Jangan memakai password contoh atau menaruh password dalam `.env`. Aplikasi tidak memerlukan secret global tambahan: sesi memakai token acak dan hash yang disimpan pada SQLite aplikasi.

## Autentikasi GHCR

Jika image bisa di-pull anonim, login registry tidak diperlukan. Jika private, gunakan token read:packages melalui password-stdin; jangan menaruh token dalam command line atau `.env` Compose. Pakai konfigurasi Docker khusus LENSA agar kredensial stack lain tidak berubah:

```bash
mkdir -p /srv/stacks/lensa/.docker
chmod 700 /srv/stacks/lensa/.docker
read -rsp 'GHCR token: ' GHCR_TOKEN; echo
printf '%s' "$GHCR_TOKEN" | docker --config /srv/stacks/lensa/.docker login ghcr.io -u pradanain --password-stdin
unset GHCR_TOKEN
chmod 600 /srv/stacks/lensa/.docker/config.json
```

Jika registry private, gunakan `DOCKER_CONFIG=/srv/stacks/lensa/.docker` pada pull/bootstrap dan `LENSA_REGISTRY_CONFIG=/srv/stacks/lensa/.docker ./deploy.sh` saat deploy. Secara default script memakai konfigurasi anonim tersendiri untuk image publik, sehingga kredensial GHCR lama pada Docker global tidak mengganggu pull dan tidak diubah. Compose memakai image yang sudah ditarik (`--pull never`).

## Deploy/update

```bash
cd /srv/stacks/lensa
./deploy.sh ghcr.io/pradanain/lensa:sha-<commit-40-digit>
```

Tanpa argumen, script memakai image dari `.env`. Script memeriksa Compose, network/subnet proxy dan ruang kosong, menarik image GHCR, mengambil backup SQLite konsisten melalui backup API, menyimpan konfigurasi privat, lalu memperbarui hanya service LENSA. Tidak ada cleanup global, penghapusan volume, atau build di server. Image lama dipertahankan dengan tag rollback; kegagalan health memulihkan image lama jika sebelumnya ada.

`/api/ready` memeriksa koneksi database; admin hanya diperiksa jika login aktif. Health check tidak mengeluarkan path, akun atau data responden. Start period 180 detik memberi waktu pembuatan index cache aplikasi pertama; tidak ada rebuild database sensus. Batas default: satu worker, CPU 1, RAM 2 GiB, PID 128, root filesystem read-only, temporary storage 128 MiB, tanpa capabilities.

## Routing dan HTTPS

Pada tunnel Cloudflare yang sudah ada, hostname `lensa.pradanain.id` harus menuju `http://traefik:80`. Jangan membuat tunnel/Traefik baru. Compose memasang Host rule, entrypoint `web`, network dan port 8000 pada label Traefik. Jangan meng-hardcode IP container. Uvicorn hanya mempercayai forwarded headers dari subnet Docker yang diverifikasi; secure cookies dan origin HTTPS dikunci oleh mode production.

Pemeriksaan setelah deploy:

```bash
cd /srv/stacks/lensa
docker compose --project-name lensa --file compose.yml ps
docker compose --project-name lensa --file compose.yml logs --tail=50 lensa
docker run --rm --network cloudflared-net curlimages/curl:8.12.1 \
  -sSI -H 'Host: lensa.pradanain.id' http://traefik:80/usaha
curl -I --max-time 20 https://lensa.pradanain.id/usaha
curl --max-time 20 https://lensa.pradanain.id/api/ready
curl -o /dev/null -w '%{http_code}\n' https://lensa.pradanain.id/api/v1/analytics/business-summary
```

Permintaan terakhir tanpa sesi harus 200 ketika login ditunda (401 jika login diaktifkan). Periksa frontend, seluruh aset JavaScript, akses tanpa login, navigasi Usaha, filter wilayah/KBLI, halaman kuesioner dan ekspor. Tes data production hanya dilakukan di browser privat; jangan mengunggah screenshot/data responden ke GitHub atau telemetry. HTTP 200 saja tidak membuktikan seluruh aplikasi berfungsi.

Menu Dashboard, Keluarga dan Raw Data sementara 403 sesuai keputusan pengembangan. Login tidak membuka halaman tersebut. Isolasi halaman tersebut tetap berlaku ketika login ditunda.

## Operasional dan rollback

```bash
cd /srv/stacks/lensa
docker compose --project-name lensa --file compose.yml logs --tail=50 lensa
docker compose --project-name lensa --file compose.yml restart lensa
LENSA_IMAGE=ghcr.io/pradanain/lensa:sha-<commit-sebelumnya> docker compose --project-name lensa --file compose.yml up -d --no-deps lensa
```

Gunakan `.rollback-image` untuk image lokal yang disimpan script, atau tag SHA sebelumnya. Tidak ada migrasi destruktif pada deployment ini. Jika versi berikutnya mengubah schema aplikasi, periksa kompatibilitas sebelum rollback image. Restore database aplikasi: hentikan **hanya LENSA**, simpan salinan state sekarang, gunakan backup SQLite yang telah diverifikasi, pulihkan ownership 10001 dan mulai LENSA. Jangan menyalin file SQLite WAL hidup dengan `cp`; gunakan backup API.

Database sensus read-only harus memiliki backup privat tersendiri. Backup akun/FTS tidak menggantikan backup dataset. Retensi backup diatur pemilik server; script tidak menghapus backup lama. Jangan menjalankan prune global.

## Troubleshooting

- Startup `PRODUCTION_ADMIN_NOT_PROVISIONED`: akun belum disiapkan; gunakan bootstrap privat, bukan membuka setup publik.
- Error trusted proxy subnet: isi `.env` dari network inspect aktual.
- 502/504: periksa health LENSA, port label 8000, keterhubungan Traefik ke network yang sama, lalu hostname tunnel. Jangan restart stack lain sebagai percobaan.
- Cookie/login: akses melalui HTTPS, periksa origin `https://lensa.pradanain.id`, secure cookie, jam server dan forwarded headers.
- Missing dataset: image tidak membawa data; transfer file privat dan cocokkan checksum.
- GHCR denied: cek visibility/package access atau gunakan kredensial read:packages pada konfigurasi Docker khusus LENSA.

Dasar konfigurasi build/publish dan precedence environment: [Docker GitHub Actions](https://docs.docker.com/build/ci/github-actions/push-multi-registries/), [Compose environment precedence](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/).


Pemeriksaan database aplikasi dan backup dilakukan sebagai UID container 10001. Folder state/backups mode 700 memang tidak dapat dibaca langsung oleh SSH user; jangan melonggarkan permission untuk mengatasi hal ini. Script tidak memakai host test -f pada database state. CI juga menjalankan rehearsal script di runner Linux sementara dengan folder state privat dan kredensial GHCR global sintetis yang salah untuk memeriksa kondisi ini.
