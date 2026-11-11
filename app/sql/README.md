# Status SQL proyek

| Lokasi | Status | Penggunaan |
| --- | --- | --- |
| `analytics/family_rosters.sql`, `analytics/social_presence.sql` | Aktif | Proyeksi baca yang dipakai semantic layer; menjaga grain dan versi |
| `analytics/foundation_*.sql` | Turunan aktif | Formula per domain yang dihasilkan dari registry; review/validasi internal |
| `validation/local_integrity.sql` | Pemeliharaan lokal | Pemeriksaan integritas lokal |
| `transformations/` | Referensi pipeline aktif | Definisi view yang dikelola kode ETL; jangan dieksekusi manual pada baseline valid |
| `source_queries/` | Referensi asal/provenance | SQL sumber historis, termasuk bukti alias UB. Path dipertahankan karena dirujuk metadata, pipeline dan tes |
| `archive/project_history/sql/blocker_reconciliation/` (dari root) | Tidak aktif | Query COUNT/versi yang telah dihentikan; dipindah keluar app/ |
| `archive/project_history/sql/counts_by_region.sql` (dari root) | Contoh lama | Query internal sebelum API terproteksi; dipindah keluar app/ |

SQL Lab ditutup permanen. File SQL sumber dipertahankan untuk memahami data lokal dan memverifikasi asal kolom. Keberadaan file tidak membuktikan query pernah dieksekusi.

Untuk dashboard gunakan `Analytics.query()`: SQL mentah tidak menerapkan penahanan sel kecil. File `foundation_*.sql` memerlukan UDF pada koneksi Analytics dan parameter terikat sesuai komentar. Registry JSON adalah sumber definisi tunggal; perubahan formula dilakukan melalui registry lalu validasi, bukan mengedit salinan SQL turunan.

Path sebelum/sesudah penataan dicatat di `data/metadata/project_reorganization_mapping.json`. Referensi path lama dalam laporan historis tetap merupakan catatan pada waktu laporan dibuat.
