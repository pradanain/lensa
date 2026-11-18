# Deployment LENSA

Target: `https://lensa.pradanain.id`, Linux Mint amd64, repository `pradanain/lensa`.

## Arsitektur

Cloudflare Tunnel existing → Traefik existing (entrypoint `web`) → satu service `lensa:8000` melalui external network `cloudflared-net`. Frontend React dibangun di GitHub dan disajikan FastAPI. Tidak ada port host, Docker socket, database service baru, atau build di server.

Image: `ghcr.io/pradanain/lensa:latest` dan `ghcr.io/pradanain/lensa:sha-<commit-40-digit>`. Untuk deployment yang dapat diulang, gunakan tag SHA atau digest. Workflow `.github/workflows/docker-publish.yml` menjalankan tes Python/React/browser, build amd64, smoke test image dengan data sintetis, lalu publish SHA dan latest. Workflow hanya memublikasikan dari `main`.

Tes Python (`verify-python`), frontend/browser (`verify`) dan simulasi deploy (`deploy-check`) berjalan paralel. Semua harus lulus sebelum job `publish` dijalankan. Push baru membatalkan run lama pada branch yang sama agar versi yang sudah diganti tidak menahan antrean. Status `cancelled` karena commit lebih baru berbeda dari kegagalan tes. Commit yang sudah ada di GitHub belum menjamin image tersedia; jalankan perintah deploy untuk SHA tersebut setelah job `publish` sukses.

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

Login dan pakta integritas aktif. Production menolak konfigurasi tanpa login. Pada `.env` server tetapkan `LENSA_AUTH_ENABLED=true` (ubah nilai `false` dari deployment lama). Akun dan hash kata sandi existing dipertahankan. Setup web production tetap ditutup; startup dan readiness memerlukan administrator aktif. Setiap sesi login baru harus menyetujui pakta sebelum data, grafik dan ekspor dibuka. Menutup dialog, Keluar atau Escape mengakhiri sesi. Persetujuan dicatat pada database aplikasi dengan versi dan waktu, tanpa data responden.

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

Permintaan terakhir tanpa sesi harus 401; setelah login tetapi sebelum pakta disetujui harus 403 COMMITMENT_REQUIRED. Setelah setuju, akses mengikuti peran akun. Periksa frontend, seluruh aset JavaScript, akses tanpa login, navigasi Usaha, filter wilayah/KBLI, halaman kuesioner dan ekspor. Tes data production hanya dilakukan di browser privat; jangan mengunggah screenshot/data responden ke GitHub atau telemetry. HTTP 200 saja tidak membuktikan seluruh aplikasi berfungsi.

Dashboard, Usaha, Keluarga dan Raw Data tersedia setelah login dan persetujuan pakta integritas.

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

- Jika deploy rollback, baca diagnostik **sebelum** pesan pemulihan image. Skrip menampilkan status container, exit code, OOM, hasil probe health, serta kode/kelas error startup yang dikenali tanpa menyalin baris log aplikasi. Log container aktif setelah rollback berasal dari image yang dipulihkan; itu tidak membuktikan penyebab kegagalan image baru. Salin `app/deploy/deploy.sh` terbaru ke `/srv/stacks/lensa/deploy.sh` agar diagnostik tersedia (pull image saja tidak memperbarui skrip host).
- Batas tunggu health sekarang 600 detik, termasuk waktu startup; dapat diubah melalui environment shell `LENSA_HEALTH_TIMEOUT_SECONDS`. Container yang berhenti, unhealthy atau tidak memiliki health check tetap langsung dianggap gagal. Batas ini memberi ruang bagi start period 180 detik dan retry Docker; menambah waktu tidak memperbaiki error startup.
- Startup `PRODUCTION_ADMIN_NOT_PROVISIONED`: akun belum disiapkan; gunakan bootstrap privat, bukan membuka setup publik.
- Error trusted proxy subnet: isi `.env` dari network inspect aktual.
- 502/504: periksa health LENSA, port label 8000, keterhubungan Traefik ke network yang sama, lalu hostname tunnel. Jangan restart stack lain sebagai percobaan.
- Cookie/login: akses melalui HTTPS, periksa origin `https://lensa.pradanain.id`, secure cookie, jam server dan forwarded headers.
- Missing dataset: image tidak membawa data; transfer file privat dan cocokkan checksum.
- GHCR denied: cek visibility/package access atau gunakan kredensial read:packages pada konfigurasi Docker khusus LENSA.

Dasar konfigurasi build/publish dan precedence environment: [Docker GitHub Actions](https://docs.docker.com/build/ci/github-actions/push-multi-registries/), [Compose environment precedence](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/).


Pemeriksaan database aplikasi dan backup dilakukan sebagai UID container 10001. Folder state/backups mode 700 memang tidak dapat dibaca langsung oleh SSH user; jangan melonggarkan permission untuk mengatasi hal ini. Script tidak memakai host test -f pada database state. CI juga menjalankan rehearsal script di runner Linux sementara dengan folder state privat dan kredensial GHCR global sintetis yang salah untuk memeriksa kondisi ini.


## Mengaktifkan login pada server yang sebelumnya tanpa akun

1. Pull image SHA terbaru yang sudah lulus CI. Jika state server masih kosong, jalankan bootstrap di atas memakai image yang sama dan nama pengguna yang Anda pilih. Masukkan kata sandi secara interaktif; jangan menaruhnya pada command line, repository atau `.env`. Bootstrap menolak mengganti akun existing. Akun yang dibuat di komputer lokal tidak otomatis tersalin ke volume server.
2. Ubah atau tambahkan `LENSA_AUTH_ENABLED=true` pada `/srv/stacks/lensa/.env`. Compose lama sudah membaca variabel ini, sehingga tidak memerlukan penggantian data atau volume.
3. Jalankan `./deploy.sh ghcr.io/pradanain/lensa:sha-<commit-terverifikasi>`. Pastikan login berhasil, pakta muncul, dan akses data baru tersedia setelah disetujui. Periksa ulang logout serta akses tanpa sesi.

## Akun sementara dan login pertama

Pendaftaran mandiri ditutup pada semua mode; endpoint setup lama tetap menolak pembuatan akun. Administrator pertama memakai bootstrap privat. Setelah masuk dan menyelesaikan onboarding, admin membuka ikon Kelola pengguna untuk mengisi nama pengguna/email, kata sandi sementara dan peran.

Semua akun baru wajib mengganti kata sandi sementara pada login pertama. Kata sandi baru minimal 8 karakter, memiliki satu huruf besar A-Z, satu angka 0-9, satu simbol (spasi bukan simbol), dan berbeda dari kata sandi lama. Konfirmasi dan kata sandi saat ini diperiksa server. Pengguna tidak dapat membuka data, ekspor, pengaturan atau menyetujui pakta sebelum selesai. Sesudah ganti, sesi lama dicabut, sesi baru diterbitkan dan pakta diminta.

Upgrade dari versi sebelum aturan ini mempertahankan akun/hash/peran existing dan menandai akun tersebut wajib ganti sekali pada login berikutnya, termasuk admin. Persetujuan pakta tetap per sesi. Tidak ada perubahan database sensus.

## Monitoring aktivitas privat

Admin membuka ikon perisai Monitoring aktivitas di header atau /monitoring. Tersedia filter akun/tindakan/hasil/tanggal, rincian request, sesi terbaru, pemeriksaan integritas dan Excel maksimal 10.000 catatan sesuai filter. Login gagal memisahkan akun yang dicoba dari pelaku terautentikasi. Catatan server mencakup login/logout, ganti password/pakta, perubahan akun, akses API/detail, pencarian dan unduhan. Klik halaman/tab/blok/roster/kontrol dilaporkan browser dan diberi penanda berbeda; browser dapat menonaktifkan atau memalsukannya. Akses lama sebelum fitur dipasang tidak dapat direkonstruksi.

Catatan menyimpan waktu UTC milidetik (UI zona perangkat), ID/peran akun, referensi sesi/request, template endpoint, metode/status/durasi, byte respons yang disiapkan, IP ASGI dan User-Agent terbatas. Isi pencarian, jawaban, cookies, kata sandi dan URL responden tidak dicatat. Referensi resource memakai HMAC, bukan ID/nama responden mentah. Aktivitas server yang tidak berhasil dicatat menghasilkan 503 sebelum data diteruskan; mutasi akun yang sudah selesai tidak otomatis dibatalkan.

activity_events dan activity_key disimpan dalam app SQLite privat. Backup konsisten database ini termasuk kuncinya; jangan unggah/commit atau membagikan ekspor monitoring. Trigger menolak edit/hapus normal dan rantai HMAC dapat diperiksa, tetapi pemilik filesystem tetap dapat memodifikasi/memulihkan database. Simpan checkpoint ID/head hash berkala pada media privat terpisah; rantai lokal sendiri tidak mendeteksi penghapusan ujung log. Tidak ada purge otomatis: pantau kapasitas disk dan tentukan retensi internal.

Pastikan LENSA_TRUSTED_PROXIES hanya proxy tepercaya sehingga IP ASGI benar. Jangan menggunakan wildcard atau mempercayai header forwarded dari sembarang klien. IP dapat bersama/VPN dan User-Agent dapat dipalsukan. Sesi masih berlaku bukan bukti pengguna sedang online; status HTTP sukses bukan bukti file telah disimpan. Foto layar, pembagian file di luar aplikasi dan pemakaian akun bersama tidak bisa dipastikan dari log ini. Jejak membantu investigasi, bukan bukti tunggal pelaku kebocoran. Seluruh pengujian menggunakan data sintetis.

## Pembaruan akun dan tampilan

Peran UI/API kini hanya Administrator dan Viewer. Viewer dapat membuka direktori/kuesioner dan mengunduh Excel. NIK/KK, kontak, alamat rinci, koordinat, kesehatan dan nominal sensitif tetap dibatasi backend; tampilan menggunakan delapan bulatan tetap. Kolom sensitif pada ekspor direktori dipertahankan dengan penanda yang sama, tanpa nilai asli atau informasi panjang/ketersediaan isian. Administrator tetap memperoleh nilai sesuai mapping dan hak akses existing.

Akun lama analyst_detail/aggregate_viewer dipetakan sebagai Viewer tanpa migrasi tabel akun. Kata sandi sementara menerima 1-256 karakter tanpa syarat kombinasi; kewajiban mengganti sandi dan kebijakan sandi baru tetap berlaku. Pakta lebih ringkas dengan tanggung jawab penuh atas data. Halaman pengguna/monitoring dirapikan untuk desktop dan ponsel. Nama KK/PJ berada di bawah nama usaha pada direktori.

Deploy setelah job publish berhasil, memakai tag SHA commit yang sudah diverifikasi. Pertahankan database sensus, state akun/audit dan konfigurasi existing; perubahan ini tidak memerlukan transfer data sensus atau provisioning ulang.
