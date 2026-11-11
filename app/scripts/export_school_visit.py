"""Export a private local school verification workbook; never log respondent rows."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'app/src'))
from se2026.web.sls_reference import SlsReference

SCHOOL = {'2': 'Tidak bersekolah lagi', '3': 'Tidak/belum pernah sekolah'}
DIPLOMA = {'00': 'Tidak punya ijazah SD', '01': 'SD/sederajat',
           '02': 'SMP/sederajat', '03': 'SMA/sederajat', '04': 'D1/D2/D3',
           '05': 'D4/S1/Profesi', '06': 'S2/S3'}


def age_years(value):
    try:
        age = Decimal(str(value))
        if age.is_finite() and age == age.to_integral_value() and 7 <= age <= 18:
            return int(age)
    except (InvalidOperation, ValueError):
        pass
    return None


def maps_link(lat, lon):
    try:
        a, b = float(lat), float(lon)
        if math.isfinite(a) and math.isfinite(b) and -90 <= a <= 90 and -180 <= b <= 180 and (a, b) != (0, 0):
            return f'https://www.google.com/maps/search/?api=1&query={a},{b}'
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def cohort(school, diploma):
    if school == '3':
        return 'Belum_pernah_sekolah'
    if diploma in ('00', '01', '02'):
        return 'Daftar_utama'
    return 'SMA_terpisah' if diploma == '03' else 'Perlu_cek_ijazah'


def suppressed_counts(counter):
    """Suppress 1-4 and a complementary group, with no totals or percentages."""
    hidden = {k for k, v in counter.items() if 0 < v < 5}
    if len(hidden) == 1:
        others = [k for k, v in counter.items() if k not in hidden and v > 0]
        if others:
            hidden.add(max(others, key=lambda k: counter[k]))
    return [(k, 'Ditahan' if k in hidden else v) for k, v in sorted(counter.items())]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def append_safe(ws, values):
    ws.append(values)
    for cell in ws[ws.max_row]:
        # Treat all source text literally, including formula-looking names/addresses.
        if isinstance(cell.value, str):
            cell.data_type = 's'
            cell.number_format = '@'


def format_sheet(ws, widths=None, filter_rows=True):
    ws.freeze_panes = 'A2'
    if filter_rows and ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.fill = PatternFill('solid', fgColor='E67E22')
        cell.font = Font(color='FFFFFF', bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical='center')
    ws.row_dimensions[1].height = 32
    for index, cells in enumerate(ws.columns, 1):
        header = str(ws.cell(1, index).value or '')
        width = (widths or {}).get(header, 22)
        ws.column_dimensions[get_column_letter(index)].width = width


def main():
    db = ROOT / 'data/processed/se2026.sqlite'
    now = datetime.now(ZoneInfo('Asia/Singapore'))
    stamp = now.strftime('%Y%m%d_%H%M%S')
    outdir = ROOT / 'data/exports' / f'verifikasi_sekolah_{stamp}'
    outdir.mkdir(parents=True, exist_ok=False)
    before = sha256(db)
    con = sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA query_only=ON')
    for table, keys in [
        ('mart_sosial_p0', 'assignment_id,__version_normalized,index1'),
        ('mart_anggota', 'assignment_id,__version_normalized,index1'),
        ('mart_keluarga', 'assignment_id,__version_normalized'),
        ('mart_assignment_tgr', 'assignment_id'),
    ]:
        if con.execute(f'SELECT 1 FROM {table} GROUP BY {keys} HAVING COUNT(*)>1 LIMIT 1').fetchone():
            raise RuntimeError('AMBIGUOUS_SOURCE_KEYS')
    rows_before = {t: con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                   for t in ['mart_sosial_p0', 'mart_anggota', 'mart_keluarga', 'mart_assignment_tgr']}
    # P0 is the anchor. Unknown ages/unmatched members remain accounted for in coverage.
    rows = con.execute('''
      SELECT s.assignment_id, s.__version_normalized, s.index1,
             s.nama_anggota, s.kode_partisipasi_sekolah, s.kode_ijazah_tertinggi,
             s.ijazah_tertinggi, s.profesi_utama, s.__conflict AS conflict_s,
             a.__key AS member_key, a.umur, a.jenis_kelamin,
             a.hubungan_kepala_keluarga, a.keberadaan_anggota,
             a.kode_keberadaan_anggota, a.status_perkawinan, a.__conflict AS conflict_a,
             f.__key AS family_key, f.nama_kk, f.alamat_keluarga,
             f.geotag_latitude, f.geotag_longitude, f.geotag_accuracy,
             f.keberadaan_keluarga, f.__conflict AS conflict_f,
             m.assignment_id AS master_key, m.kode_kecamatan, m.kecamatan,
             m.kode_desa, m.desa_kelurahan, m.kode_sls, m.kode_subsls,
             m.status_assignment
      FROM mart_sosial_p0 s
      LEFT JOIN mart_anggota a
        ON a.assignment_id=s.assignment_id AND a.__version_normalized=s.__version_normalized AND a.index1=s.index1
      LEFT JOIN mart_keluarga f
        ON f.assignment_id=s.assignment_id AND f.__version_normalized=s.__version_normalized
      LEFT JOIN mart_assignment_tgr m ON m.assignment_id=s.assignment_id
      WHERE s.kode_partisipasi_sekolah IN ('2','3')
    ''').fetchall()
    ref = SlsReference(ROOT)
    wb = Workbook()
    notes = wb.active
    notes.title = 'PETUNJUK'
    headers = ['No', 'Kelompok sekolah', 'Kelompok ijazah', 'Nama anak', 'Umur',
               'Kelompok umur', 'Jenis kelamin', 'Nama kepala keluarga', 'Kecamatan',
               'Desa kelurahan', 'SLS RT RW', 'SUB-SLS', 'Alamat keluarga',
               'Latitude keluarga', 'Longitude keluarga', 'Maps', 'Status tagging',
               'Akurasi tagging sumber', 'Keberadaan anak', 'Prioritas kunjungan',
               'Hubungan dengan KK', 'Status perkawinan', 'Profesi utama',
               'Keberadaan keluarga', 'Status assignment', 'Status cocok keluarga',
               'Status referensi SLS', 'Kode kecamatan', 'Kode desa', 'Kode SLS',
               'Kode SUB-SLS', 'Assignment ID', 'Versi kuesioner', 'Indeks ART',
               'Kode sekolah', 'Kode ijazah', 'Konflik sumber',
               'Tanggal kunjungan', 'Hasil verifikasi sekolah', 'Catatan petugas']
    sheets = {name: wb.create_sheet(name) for name in
              ['Daftar_utama', 'SMA_terpisah', 'Belum_pernah_sekolah', 'Perlu_cek_ijazah']}
    for ws in sheets.values():
        append_safe(ws, headers)
    selected, seen = [], set()
    quality = Counter()
    for r in rows:
        age = age_years(r['umur'])
        if age is None:
            quality['status_target_tanpa_umur_7_18_valid'] += 1
            if not r['member_key']:
                quality['status_target_tanpa_match_anggota'] += 1
            continue
        key = (r['assignment_id'], r['__version_normalized'], r['index1'])
        if key in seen:
            raise RuntimeError('JOIN_MULTIPLICATION')
        seen.add(key)
        group = cohort(r['kode_partisipasi_sekolah'], r['kode_ijazah_tertinggi'])
        geo = ref.describe(r['kode_sls'], r['kode_subsls'])
        link = maps_link(r['geotag_latitude'], r['geotag_longitude'])
        age_band = '7–12' if age <= 12 else '13–15' if age <= 15 else '16–18'
        priority = ('Kunjungan: tinggal/anggota baru' if r['kode_keberadaan_anggota'] in ('1', '5')
                    else 'Periksa keberadaan sebelum kunjungan')
        diploma = DIPLOMA.get(r['kode_ijazah_tertinggi'], 'Ijazah kosong/tidak dikenali')
        flags = '; '.join(name for name, val in [('P0', r['conflict_s']), ('ART', r['conflict_a']), ('KELUARGA', r['conflict_f'])]
                          if val not in (None, '', 0, '0'))
        values = [len(selected)+1, SCHOOL[r['kode_partisipasi_sekolah']], diploma,
                  r['nama_anggota'], age, age_band, r['jenis_kelamin'], r['nama_kk'],
                  r['kecamatan'], r['desa_kelurahan'], geo['sls_label'],
                  r['kode_subsls'][-2:] if geo['geography_reference_status']=='SUBSLS_EXACT' and r['kode_subsls'][-2:]!='00' else None,
                  r['alamat_keluarga'], r['geotag_latitude'], r['geotag_longitude'], link,
                  'Valid: root keluarga versi tepat' if link else 'Kosong/tidak valid/tidak cocok keluarga',
                  r['geotag_accuracy'], r['keberadaan_anggota'], priority,
                  r['hubungan_kepala_keluarga'], r['status_perkawinan'], r['profesi_utama'],
                  r['keberadaan_keluarga'], r['status_assignment'],
                  'Cocok assignment + versi' if r['family_key'] else 'Tidak cocok: jangan isi lintas versi',
                  geo['geography_reference_status'], r['kode_kecamatan'], r['kode_desa'],
                  r['kode_sls'], r['kode_subsls'], r['assignment_id'], r['__version_normalized'],
                  r['index1'], r['kode_partisipasi_sekolah'], r['kode_ijazah_tertinggi'], flags or 'Tidak',
                  None, None, None]
        ws = sheets[group]
        append_safe(ws, values)
        if link:
            ws.cell(ws.max_row, headers.index('Maps')+1).hyperlink = link
            ws.cell(ws.max_row, headers.index('Maps')+1).style = 'Hyperlink'
        selected.append(dict(row=r, sheet=group, age_band=age_band, diploma=diploma))
        quality['tagging_valid' if link else 'tagging_tidak_tersedia_valid'] += 1
        quality['keluarga_cocok' if r['family_key'] else 'keluarga_tidak_cocok'] += 1
        quality['prioritas_tinggal_baru' if r['kode_keberadaan_anggota'] in ('1','5') else 'cek_keberadaan_dahulu'] += 1
    # Every child appears exactly once across the four private detail sheets.
    expected = sum(age_years(r['umur']) is not None for r in rows)
    assert len(selected) == len(seen) == expected
    selected.sort(key=lambda x: (x['sheet'], x['row']['kode_kecamatan'] or '', x['row']['kode_desa'] or '',
                                 x['row']['kode_sls'] or '', x['row']['nama_kk'] or '', x['row']['nama_anggota'] or ''))
    # Sort within each sheet by geography, household, then child, retaining literal types and links.
    for ws in sheets.values():
        data = list(ws.iter_rows(min_row=2, values_only=True))
        data.sort(key=lambda v: tuple(str(v[headers.index(k)] or '') for k in
                                     ['Kode kecamatan','Kode desa','Kode SLS','Nama kepala keluarga','Nama anak','Assignment ID','Indeks ART']))
        if ws.max_row > 1:
            ws.delete_rows(2, ws.max_row-1)
        for values in data:
            append_safe(ws, list(values))
            link = values[headers.index('Maps')]
            if link:
                ws.cell(ws.max_row, headers.index('Maps')+1).hyperlink = link
                ws.cell(ws.max_row, headers.index('Maps')+1).style = 'Hyperlink'
        format_sheet(ws, {'Nama anak':32, 'Nama kepala keluarga':32, 'Alamat keluarga':48, 'Maps':18,
                          'Kecamatan':25, 'Desa kelurahan':28, 'SLS RT RW':25, 'Assignment ID':39,
                          'Catatan petugas':45, 'Status tagging':35, 'Prioritas kunjungan':42})
    for title, dimensions, get_key in [
        ('Rekap_wilayah', ['Kode kecamatan','Kecamatan','Kode desa','Desa','Kelompok'],
         lambda x: tuple(str(x['row'][k] or 'Belum tersedia') for k in ['kode_kecamatan','kecamatan','kode_desa','desa_kelurahan'])+(x['sheet'],)),
        ('Rekap_umur_JK', ['Kelompok','Kelompok umur','Jenis kelamin'],
         lambda x: (x['sheet'],x['age_band'],x['row']['jenis_kelamin'] or 'Belum tersedia')),
        ('Rekap_ijazah', ['Partisipasi sekolah','Ijazah'],
         lambda x: (SCHOOL[x['row']['kode_partisipasi_sekolah']],x['diploma'])),
    ]:
        ws = wb.create_sheet(title)
        append_safe(ws, dimensions+['Jumlah ART (supresi <5)'])
        for key, count in suppressed_counts(Counter(get_key(x) for x in selected)):
            append_safe(ws, list(key)+[count])
        format_sheet(ws)
    notes_rows = [
        ('Judul', 'LENSA SE2026 Kabupaten Bulungan — daftar verifikasi sekolah usia 7–18 tahun'),
        ('Dibuat', now.isoformat()),
        ('Penggunaan', 'Data pribadi untuk verifikasi/kunjungan internal, simpan lokal. Bukan daftar putus sekolah terkonfirmasi.'),
        ('Daftar_utama', 'Tidak bersekolah lagi; ijazah tidak punya SD, SD/sederajat atau SMP/sederajat. Gunakan filter Kelompok ijazah.'),
        ('SMA_terpisah', 'Tidak bersekolah lagi dengan ijazah SMA/sederajat; tidak otomatis putus sekolah.'),
        ('Belum_pernah_sekolah', 'Kode sumber 3: tidak/belum pernah sekolah; kelompok terpisah dari pernah sekolah lalu berhenti.'),
        ('Perlu_cek_ijazah', 'Tidak bersekolah lagi dengan ijazah kosong/tidak dikenali atau pendidikan tinggi; dipertahankan untuk verifikasi.'),
        ('Kriteria umur', 'Umur bulat 7 sampai 18 inklusif dari ART yang cocok P0 pada assignment + versi + index1. Tidak menghitung ulang dari tanggal lahir.'),
        ('Keberadaan', 'Semua status dipertahankan. Filter Prioritas kunjungan dan Keberadaan anak; tinggal/anggota baru lebih dahulu, cek status pindah/meninggal/pisah KK/tidak ditemukan sebelum visit.'),
        ('Nama KK dan alamat', 'Hanya mart_keluarga dengan assignment + versi sama. Tidak ada pengisian nama atau alamat lintas versi.'),
        ('Tagging', 'Titik root keluarga versi tepat, bukan titik khusus anak. Tidak memakai koordinat operasional assignment sebagai pengganti; tidak memverifikasi posisi lapangan.'),
        ('Maps', 'Tautan dibuat lokal; tidak ada request eksternal otomatis. Klik membuka koordinat pada Google Maps.'),
        ('SLS', 'Label referensi 2025_2 pada kode penuh 14/16 digit; tanpa tebakan RT/RW. SLS tidak cocok dibiarkan kosong, kode sumber dipertahankan. SUB 00 tidak ditampilkan pada label.'),
        ('Wilayah', 'Kecamatan/desa/SLS dari master assignment, bukan asumsi domisili anak saat ini.'),
        ('Identitas', 'Satu baris per assignment + versi + indeks ART. Nama tidak menjadi kunci. ID/kode tetap TEXT; NIK/nomor KK tidak diekspor.'),
        ('Cakupan', 'Snapshot lokal DTD/TGR tgr_fd68e454; tanpa pencampuran UB. Tidak memfilter ulang status assignment selesai; status sumber disertakan agar dapat dipilah.'),
        ('Keterbatasan', 'Alasan berhenti, kelas terakhir dan waktu berhenti belum tersedia. Status sekolah bisa berubah setelah pendataan; konfirmasi saat kunjungan.'),
        ('Isian lapangan', 'Tanggal kunjungan, Hasil verifikasi sekolah dan Catatan petugas sengaja kosong untuk diisi saat visit.'),
        ('Rekap', 'Jumlah 1–4 ditahan; satu kelompok tambahan ditahan bila perlu. Tanpa total/persentase pada rekap. Daftar individu adalah keluaran privat yang diminta untuk visit, bukan publikasi.'),
        ('Database SHA-256', before),
    ]
    append_safe(notes, ['Keterangan','Isi'])
    for row in notes_rows:
        append_safe(notes, list(row))
    format_sheet(notes, {'Keterangan':28,'Isi':115}, False)
    for row in notes.iter_rows(min_row=2):
        row[1].alignment = Alignment(wrap_text=True, vertical='top')
        notes.row_dimensions[row[0].row].height = 48
    path = outdir / 'DAFTAR_VERIFIKASI_SEKOLAH_7_18.xlsx'
    wb.save(path)
    check = load_workbook(path, read_only=True, data_only=False)
    actual = sum(check[name].max_row-1 for name in sheets)
    assert actual == expected
    assert not any(cell.data_type=='f' for ws in check for row in ws for cell in row)
    check.close()
    integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
    fk_errors = len(con.execute('PRAGMA foreign_key_check').fetchall())
    rows_after = {t: con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in rows_before}
    con.close()
    after = sha256(db)
    assert before == after and rows_before == rows_after and integrity == 'ok' and fk_errors == 0
    counts = dict(Counter(x['sheet'] for x in selected))
    report = dict(created_at=now.isoformat(), export_type='PRIVATE_LOCAL_VISIT_LIST',
                  source_system='tgr_fd68e454', database='data/processed/se2026.sqlite',
                  database_sha256_before=before, database_sha256_after=after,
                  workbook_sha256=sha256(path), workbook=str(path.relative_to(ROOT)),
                  selection='P0 school code 2 or 3, exact-match ART integer age 7..18; all existence/assignment statuses retained',
                  mapping={'education':'mart_sosial_p0', 'age_existence':'mart_anggota exact assignment/version/index1',
                           'head_address_tagging':'mart_keluarga exact assignment/version',
                           'geography_status':'mart_assignment_tgr assignment_id', 'sls_reference':'2025_2'},
                  selected_rows=actual, sheets=counts, coverage=dict(quality), source_row_counts_before=rows_before,
                  source_row_counts_after=rows_after, integrity_check=integrity, foreign_key_errors=fk_errors,
                  unique_selected_keys=len(seen), no_join_multiplication=True, workbook_reopened=True,
                  formula_cells=0, respondent_values_logged=False)
    report_path = ROOT / 'docs/reports/analytics' / f'school_visit_export_{stamp}.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (outdir / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'workbook':str(path.relative_to(ROOT)), 'selected_rows':actual,
                      'sheets':counts, 'coverage':dict(quality), 'database_unchanged':before==after,
                      'report':str(report_path.relative_to(ROOT))}, ensure_ascii=False))


if __name__ == '__main__':
    main()
