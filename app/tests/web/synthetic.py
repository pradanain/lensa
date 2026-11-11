"""Small, explicitly synthetic SQLite contract for API/browser tests."""

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V1 = "2026-09-01T00:00:00.000000"
V2 = "2026-09-02T00:00:00.000000"


def make_database(path, root=ROOT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError("SYNTHETIC_DATABASE_ALREADY_EXISTS")
    config = json.loads((root / "app/config/sources.json").read_text(encoding="utf-8"))["sources"]
    analytics = json.loads((root / "app/config/analytics/sources.json").read_text(encoding="utf-8"))
    con = sqlite3.connect(path)
    schemas = {}
    systems = {}
    for source in config:
        sid = source["id"]
        columns = set(source["columns"]) | {
            "assignment_id",
            "__version_normalized",
            "__row_id",
            "__key",
            "__key_valid",
            "__conflict",
            "__import_id",
            "__source_sha256",
            "__batch_id",
        }
        if sid.startswith("ub_"):
            columns.add("id_penghubung")
        schemas["mart_" + sid] = columns
        systems["mart_" + sid] = source["system"]
    for source in analytics.values():
        if source.get("query"):
            continue
        schemas.setdefault(source["view"], set()).update(source["columns"])
        systems[source["view"]] = source["system"]
    for view, columns in schemas.items():
        con.execute(
            'CREATE TABLE "' + view + '"(' + ",".join('"' + col + '" TEXT' for col in sorted(columns)) + ")"
        )
        for n in range(1, 13):
            system = systems[view]
            aid = ("UB-" if system == "TCZ" else "DTD-") + str(n).zfill(4)
            row = {col: None for col in columns}
            row.update({col: "1" for col in columns if col.startswith("has_")})
            row.update(
                assignment_id=aid,
                id_penghubung=aid,
                __version_normalized=V1,
                __row_id=str(n),
                __key_valid="1",
                __conflict="0",
                __import_id="1",
                __source_sha256="synthetic-sha",
                __batch_id="synthetic-batch",
                index1="001",
                index_usaha="001",
                index_kantor_unit="001",
                index_meteran="001",
                assignment_date_modified=V1,
                kode_kabupaten="6502",
                kode_kecamatan="6502010" if n < 11 else "6502000",
                kode_desa="6502010001" if n < 11 else "6502000000",
                kode_sls="65020100010001" if n < 11 else "65020000000000",
                kode_subsls="6502010001000101",
                kecamatan="KECAMATAN SINTETIS",
                desa_kelurahan="DESA SINTETIS",
                sls="SLS SINTETIS",
                subsls="SUB SINTETIS",
                versi_root_terbaru=V1,
                status_assignment="APPROVED BY Pengawas",
                kode_status_assignment="APPROVED BY Pengawas",
                status_kuesioner="ADA_KUESIONER",
                nama_kk="KELUARGA SINTETIS " + str(n),
                nama_usaha="USAHA SINTETIS " + str(n),
                nama_anggota="ANGGOTA SINTETIS " + str(n),
                nama_bangunan_usaha="BKU SINTETIS " + str(n),
                nama_kantor_unit="KANTOR SINTETIS " + str(n),
                nik_kk="SYNTHETIC_PRIVATE_NIK",
                no_kk="SYNTHETIC_PRIVATE_KK",
                nik_anggota="SYNTHETIC_PRIVATE_NIK",
                nik_penanggung_jawab="SYNTHETIC_PRIVATE_NIK",
                nib="SYNTHETICNIB" + str(n),
                kode_keberadaan_keluarga="1",
                keberadaan_keluarga="Ditemukan",
                kode_keberadaan_usaha="1",
                keberadaan_usaha="Ditemukan",
                kode_keberadaan_bku="1",
                keberadaan_bku="Ditemukan",
                kode_keberadaan_anggota="1",
                keberadaan_anggota="Ditemukan",
                status_keberadaan="1. Ditemukan dan masih aktif",
                kbli="01111" if n < 10 else None if n == 10 else "INVALID" if n == 11 else "99999",
                kbli_akhir="01111",
                kategori="A",
                kategori_kbli="A",
                umur="30",
                kode_jenis_kelamin="1",
                jenis_kelamin="Laki-laki",
                kode_partisipasi_sekolah="2",
                partisipasi_sekolah="Tidak sekolah",
                kode_ijazah_tertinggi="3",
                ijazah_tertinggi="SMA",
                kode_profesi_utama="000",
                profesi_utama="Tidak Bekerja",
                profesi_lainnya="SYNTHETIC_OTHER_PROFESSION",
                kode_menggunakan_internet="2" if n == 1 else "1",
                menggunakan_internet="2. Tidak" if n == 1 else "1. Ya",
                internet_menerima_pesanan=None,
                internet_pesanan=None,
                pekerja_laki_laki="2",
                pekerja_perempuan="3",
                total_pekerja_jenis_kelamin="5",
                jumlah_pekerja="5",
                status_konsistensi_pekerja="SESUAI",
                total_pendapatan_2025="12345678901234567890.10",
                total_pengeluaran_2025="10.00",
                total_aset_2025="20.00",
                total_pendapatan="42.10",
                total_pengeluaran="10.00",
                total_aset="20.00",
                nilai_pend_pekerjaan="SYNTHETIC_OPAQUE_INCOME",
                total_pendapatan_pekerjaan="45.00",
                status_kepemilikan="1",
            )
            for key in columns:
                if key.endswith("_label") and key.startswith(("dis_", "sakit_")):
                    row[key] = "SYNTHETIC_PRIVATE_HEALTH"
                if key.endswith("_value") and key.startswith(("dis_", "sakit_")):
                    row[key] = "1"
            if view == "mart_p1_pekerjaan" and n == 1:
                row["__version_normalized"] = V2
                row["assignment_date_modified"] = V2
            row["__key"] = hashlib.sha256(
                (view + aid + str(row["__version_normalized"]) + "001").encode()
            ).hexdigest()
            cols = sorted(columns)
            con.execute(
                'INSERT INTO "'
                + view
                + '"('
                + ",".join('"' + c + '"' for c in cols)
                + ") VALUES("
                + ",".join("?" for _ in cols)
                + ")",
                [row.get(c) for c in cols],
            )
    # One parent has a second business/member; a direct child join would multiply.
    for view in ("mart_usaha", "mart_anggota", "mart_p1_pekerjaan"):
        cols = [r[1] for r in con.execute('PRAGMA table_info("' + view + '")')]
        old = list(
            con.execute('SELECT * FROM "' + view + '" WHERE assignment_id=?', ("DTD-0001",)).fetchone()
        )
        old[cols.index("index1")] = "002"
        old[cols.index("__version_normalized")] = V1
        old[cols.index("__row_id")] = "99"
        old[cols.index("__key")] = "synthetic-second-" + view
        if "nama_usaha" in cols:
            old[cols.index("nama_usaha")] = "USAHA SINTETIS KEDUA"
        if "nama_anggota" in cols:
            old[cols.index("nama_anggota")] = "ANGGOTA SINTETIS KEDUA"
        con.execute('INSERT INTO "' + view + '" VALUES(' + ",".join("?" for _ in cols) + ")", old)
    # Master assignment without detail must remain in the directory.
    con.execute(
        "INSERT INTO mart_assignment_tgr(assignment_id,kecamatan,desa_kelurahan,kode_kecamatan,kode_desa,kode_sls,status_assignment,status_kuesioner,__row_id,__version_normalized) VALUES('DTD-EMPTY','KECAMATAN SINTETIS','DESA SINTETIS','6502010','6502010001','65020100010001','1','TANPA_KUESIONER','99','')"
    )
    con.execute("CREATE TABLE active_imports(source_id TEXT PRIMARY KEY,import_id INTEGER)")
    con.execute(
        "CREATE TABLE imported_files(import_id INTEGER PRIMARY KEY,source_id TEXT,sha256 TEXT,batch_id TEXT)"
    )
    for number, source in enumerate(config, 1):
        sid = source["id"]
        view = "mart_" + sid
        con.execute('UPDATE "' + view + '" SET __import_id=?', (str(number),))
        con.execute('CREATE TABLE "clean_' + sid + '" AS SELECT * FROM "' + view + '"')
        con.execute("INSERT INTO active_imports VALUES (?,?)", (sid, number))
        con.execute(
            "INSERT INTO imported_files VALUES (?,?,?,?)", (number, sid, "synthetic-sha", "synthetic-batch")
        )
        con.execute(
            'CREATE INDEX "ix_join_'
            + sid
            + '" ON "clean_'
            + sid
            + '"(__import_id,assignment_id,__version_normalized)'
        )
    con.commit()
    con.close()
    path.with_suffix('.sls.json').write_text(json.dumps({
        'period':'2025_2', 'rows':[
            {'code':'6502010001000101','sls':'65020100010001','label':'RT 001 / RW 002','rt':'001','rw':'002','kind':'SLS'},
            {'code':'6502010001000102','sls':'65020100010001','label':'RT 001 / RW 002','rt':'001','rw':'002','kind':'SLS'},
        ]
    }),encoding='utf-8')
    return path
