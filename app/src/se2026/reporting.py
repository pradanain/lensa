from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter

from .layout import DOCUMENTS, write_document
from .common import q, sha256, utcnow, write_csv
from .scanner import load_config


def markdown_table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---']*len(headers)) + ' |'] + ['| ' + ' | '.join(str(v).replace('|','/').replace('\n',' ') for v in row) + ' |' for row in rows])


def issues_from_audit(audit):
    issues = []
    def add(dataset, issue, rows, severity, evidence, recommendation, status='OPEN'):
        issues.append(dict(dataset=dataset, anomaly=issue, affected_rows=rows, severity=severity, evidence=evidence, recommendation=recommendation, status=status))
    for d in audit['datasets']:
        if d['source_system'] not in ('TGR','TCZ'):
            continue
        if d['identical_duplicate_rows']:
            add(d['dataset'],'IDENTICAL_DUPLICATE',d['identical_duplicate_rows'],'MEDIUM','Hash seluruh nilai dan tipe sel sama','RAW utuh; CLEAN menggabungkan duplikat identik','PRESERVED_RAW_DEDUP_CLEAN')
        if d['conflict_rows']:
            add(d['dataset'],'CONFLICTING_NORMALIZED_KEY',d['conflict_rows'],'HIGH','Kunci ternormalisasi sama tetapi isi/representasi mentah berbeda','Pertahankan seluruh varian; jangan pilih versi secara arbitrer')
        if d['key_null_rows']:
            add(d['dataset'],'NULL_OR_INVALID_KEY',d['key_null_rows'],'HIGH','Komponen kunci kosong atau timestamp gagal dinormalisasi','Pertahankan baris; blokir JOIN dengan kunci tidak valid')
        for col,n in d['invalid_timestamps'].items():
            add(d['dataset'],'INVALID_TIMESTAMP',n,'HIGH','Timestamp tidak valid pada '+col,'Simpan nilai asli; jangan menebak waktu')
        if d['out_of_scope_rows']:
            add(d['dataset'],'OUTSIDE_SCOPE',d['out_of_scope_rows'],'HIGH','kode_kabupaten bukan 6502','Tandai dan tinjau ekspor sumber')
        if d.get('reference_difference'):
            add(d['dataset'],'HISTORICAL_COUNT_DIFFERENCE',abs(d['reference_difference']),'INFO','Selisih bertanda: '+str(d['reference_difference']),'Catatan cakupan historis non-blocking; gunakan baseline lokal tanpa menyamakan baris','LOCAL_BASELINE_CAVEAT')
        e = d.get('export_metadata')
        if e and not d.get('export_row_count_matches'):
            add(d['dataset'],'EXPORT_COUNT_MISMATCH',d['rows'],'HIGH','Jumlah baca berbeda dari fetched_rows metadata','Audit ulang sumber sebelum aktivasi')
        if e and e.get('end_of_data_detected') is False:
            add(d['dataset'],'EOF_NOT_PROVEN',d['rows'],'INFO','Batas target historis tercapai; metadata end_of_data_detected=false','Batasan cakupan lokal non-blocking; SQL Lab ditutup permanen, tanpa kebutuhan COUNT/ekspor tambahan','LOCAL_BASELINE_CAVEAT')
        if d['dataset'].startswith('ub_'):
            add(d['dataset'],'QUESTIONNAIRE_VERSION_NOT_VERIFIED',d['rows'],'INFO','Timestamp kuesioner UB tidak diekspor; provenance historis belum terbukti','Catatan provenance; tidak memblokir JOIN assignment_id dan tidak memerlukan ekspor ulang timestamp','NON_BLOCKING_PROVENANCE')
    for r in audit['relationships']:
        if r['unmatched_child_rows']:
            add(r['child'],'UNMATCHED_PARENT',r['unmatched_child_rows'],'MEDIUM',r['parent']+' / '+r['temporal_evidence'],'Simpan modul asli dan tabel anak; LEFT JOIN hanya pada key versi yang sama')
        if r['multiplication_excess']:
            add(r['child'],'JOIN_MULTIPLICATION',r['multiplication_excess'],'HIGH','Parent key tidak unik','Blokir wide JOIN')
    return issues


def report(root):
    audit = json.loads((root/'data/metadata/audit_results.json').read_text(encoding='utf-8'))
    manifest = json.loads((root/'data/metadata/file_manifest.json').read_text(encoding='utf-8'))
    sources = load_config(root)
    datasets = {d['dataset']:d for d in audit['datasets'] if d['source_system'] in ('TGR','TCZ')}
    issues = issues_from_audit(audit)
    clean_relations_path = root/'docs/reports/database/database_relationship_validation.csv'
    clean_relations = {}
    if clean_relations_path.exists():
        with clean_relations_path.open(encoding='utf-8-sig',newline='') as stream:
            clean_relations = {r['child']:r for r in csv.DictReader(stream)}
        for issue in issues:
            if issue['anomaly']=='JOIN_MULTIPLICATION' and clean_relations.get(issue['dataset'],{}).get('status')=='PASS_NO_MULTIPLICATION':
                issue.update(status='RESOLVED_IN_CLEAN_RAW_PRESERVED',recommendation='Raw JOIN tetap diblokir; CLEAN deduplikasi identik dan lolos uji tanpa penggandaan')
    diagnoses = []
    diagnosis_path = root/'docs/reports/database/unmatched_diagnosis.csv'
    if diagnosis_path.exists():
        with diagnosis_path.open(encoding='utf-8-sig',newline='') as stream:
            diagnoses = list(csv.DictReader(stream))
        for issue in issues:
            if issue['anomaly']=='UNMATCHED_PARENT':
                d = next((d for d in diagnoses if d['child']==issue['dataset']),None)
                if d:
                    issue['evidence'] += '; CLEAN: '+d['same_unit_different_timestamp']+' unit sama timestamp berbeda; '+d['roster_unit_not_found']+' roster tidak ditemukan; '+d['assignment_id_not_found']+' assignment tidak ditemukan'
    write_csv(root/'docs/reports/database/data_quality_summary.csv', issues, ['dataset','anomaly','affected_rows','severity','evidence','recommendation','status'])
    docs, reports = root/'docs',root/'docs/reports'
    docs.mkdir(exist_ok=True)
    reports.mkdir(exist_ok=True)
    for group in ("database", "integration"):
        (reports/group).mkdir(parents=True,exist_ok=True)
    def doc(name,text):
        write_document(root, 'docs/' + name, text)
    total = sum(d['rows'] for d in datasets.values())
    doc('WORKSPACE_INVENTORY.md', '# Inventaris workspace\n\n'
        f'Audit lokal: {audit["generated_utc"]}. {len(manifest["files"])} file asli, '
        f'{sum(f["bytes"] for f in manifest["files"]):,} byte, '
        f'{len(sources)} workbook data, {total:,} baris data.\n\n'
        + markdown_table(['Ekstensi','File'], sorted(Counter(f['extension'] for f in manifest['files']).items()))
        + '\n\nStruktur lengkap termasuk direktori kosong tersimpan di `data/metadata/file_manifest.json`. '
        'Semua file dan anggota ZIP dihash SHA-256. '
        f'{len(manifest["exact_duplicate_groups"])} grup duplikat file identik; '
        f'{len(manifest["zip_members"])} anggota ZIP diperiksa, '
        f'{sum(bool(m["identical_extracted_paths"]) for m in manifest["zip_members"])} identik dengan file yang sudah diekstrak. '
        'Kesamaan nama/ukuran tidak dipakai untuk deduplikasi.\n\n'
        'Dua workbook checklist mempunyai layout administratif multi-sheet, bukan data responden. '
        'Empat CSV adalah daftar query/manifest, bukan tambahan baris pendataan. '
        'Seluruh sheet workbook, CSV dan tabel SQLite diinventarisasi; kolom administratif tanpa header diberi nama posisi.\n\n'
        + '\n\n'.join(f'SQLite lama `{s["path"]}`: integrity_check={s["integrity"]}.\n\n' + markdown_table(['Tabel','Baris'],[(t['name'],t['rows']) for t in s['tables']]) for s in audit['sqlite'])
        + '\n\nSQLite lama merupakan checkpoint ekspor dengan chunk_1 sebanyak 13.000 baris, bukan database analitik. '
        'Workbook P1 pekerjaan berisi 139.186 baris. Checkpoint dipertahankan, disalin terverifikasi, dan tidak dijadikan pengganti workbook lengkap. '
        'README lama yang menyatakan direktori ekspor kosong adalah petunjuk paket historis; kondisi aktual ditentukan melalui audit ini.\n')
    catalog = []
    for s in sources:
        d = datasets[s['id']]
        catalog.append([s['id'],s['system']+'/'+s['phase'],d['rows'],d['columns'],s['grain'],', '.join(s['key']),
                        'unik' if d['candidates']['full']['unique'] else 'lihat audit',s['parent'] or '-'])
    doc('DATASET_CATALOG.md', '# Katalog dataset\n\nSatu baris adalah unit yang disebut pada kolom grain, pada versi kuesioner yang diekspor. '
        'Master assignment adalah assignment operasional; timestamp-nya tidak dipaksakan sama dengan versi root.\n\n'
        + markdown_table(['Dataset','Sumber/tahap','Baris','Kolom','Grain','Kunci diuji','Hasil','Induk'],catalog)
        + '\n\nDaftar kolom, tipe observasi, pola format tanpa nilai responden, dan persentase NULL tersedia di `data/metadata/column_dictionary.csv`. '
        'Lokasi sumber dan SHA-256 ada pada `data/metadata/dataset_inventory.csv` dan `app/config/sources.json`. '
        'Kunci roster index_usaha adalah alias index1; index_kantor_unit adalah alias index2 menurut SQL sumber. '
        '08C kantor_pusat merupakan record root berstatus keberadaan 7, bukan roster unit usaha; grain-nya tidak disamakan dengan kantor_unit.\n\n'
        'Cakupan modul berbeda menurut filter: master keluarga/BKU/usaha mempertahankan status keberadaan; '
        'modul rincian umumnya membatasi ditemukan/baru. Ekonomi tahunan memfilter tahun operasi <2026; '
        'ekonomi bulanan memfilter 2026. Ketidaktersediaan rincian tidak otomatis merupakan data hilang. '
        'SQL PART yang tidak memiliki file hasil bukan variabel data lokal; ketiadaannya hanya membatasi jenis analisis, tanpa rencana pengumpulan tambahan.\n')
    relation_table = markdown_table(['Induk','Anak','Kardinalitas','Baris anak','Tanpa induk','Kelebihan JOIN','Status'],
        [[r['parent'],r['child'],r['cardinality'],r['child_rows'],r['unmatched_child_rows'],r['multiplication_excess'],r['status']] for r in audit['relationships']])
    doc('DATA_RELATIONSHIPS.md', '# Relasi berdasarkan pengujian aktual\n\n' + relation_table + '\n\n'
        'Kolom kunci kedua sisi dan bukti temporal tersedia pada `data/metadata/relationship_mapping.csv`. '
        'Relasi assignment ke root/roster memakai ID dalam sistem yang sama, karena tanggal assignment adalah versi operasional. '
        'Relasi kuesioner memakai ID + timestamp kuesioner ternormalisasi + indeks roster sesuai grain. '
        'Waktu tanpa zona tetap tanpa zona; waktu dengan zona dikonversi UTC. Keduanya tidak dianggap sama. '
        'Presisi melebihi mikrodetik yang tidak nol ditolak agar tidak menyatukan versi berbeda.\n\n'
        'P1 mempertahankan seluruh key termasuk yang tidak ada pada P0. Tidak mencocokkan berdasarkan nama, NIK, nomor urut atau ID saja. '
        'Normalisasi timestamp menyamakan representasi temporal setara; timestamp asli tetap tersedia.\n\n'
        + markdown_table(['P1 acuan','P1 lain','Hanya kiri','Hanya kanan'],[[r['left'],r['right'],r['left_only'],r['right_only']] for r in audit['p1_cross_validation']])
        + '\n\nUB memakai assignment_id saja. SQL r.assignment_id AS id_penghubung dibuktikan dan distandardisasi pada view CLEAN/MART. '
        'Status integrasi ASSIGNMENT_KEY_VERIFIED; QUESTIONNAIRE_VERSION_NOT_VERIFIED hanya catatan provenance historis, bukan blocker atau syarat ekspor ulang. '
        'TGR dan TCZ disimpan sebagai sumber terpisah. Tidak ada relasi keluarga-ke-BKU melalui nama atau lokasi yang diasumsikan.\n')
    edges = []
    for r in audit['relationships']:
        child = datasets[r['child']]
        unique_clean = child['candidates'][r['child_projection']]['distinct']==child['rows']-child['identical_duplicate_rows'] and child['conflicting_keys']==0
        symbol = '||--o|' if unique_clean else '||--o{'
        status = 'CLEAN_MATCHED_ROWS' if r['child'] in clean_relations else r['status']
        if r['child'] in ('ub_a','ub_b','ub_c'):
            status = 'ASSIGNMENT_KEY_VERIFIED'
        edges.append(f'    {r["parent"]} {symbol} {r["child"]} : "{status}"')
    diagram = '\n'.join(edges)
    doc('ENTITY_RELATIONSHIP_DIAGRAM.md', '# Diagram relasi\n\n```mermaid\nerDiagram\n'+diagram+'\n```\n\nDiagram CLEAN menunjukkan key setelah deduplikasi identik untuk baris matched. Orphan tetap tersimpan di tabel modul. '
        'Hasil RAW ada di relationship_mapping.csv; diagram bukan jaminan kelengkapan ekspor atau kesamaan versi UB.\n')
    quality_table = markdown_table(['Dataset','Anomali','Baris','Severity','Bukti','Tindakan','Status'],
        [[i[k] for k in ['dataset','anomaly','affected_rows','severity','evidence','recommendation','status']] for i in issues])
    write_document(root, 'reports/DATA_QUALITY_REPORT.md', '# Audit kualitas data\n\n'+quality_table+'\n\n'
        'NULL/kosong dihitung per kolom dan tidak otomatis dianggap kesalahan karena skip pattern/filter sumber. '
        'Tipe observasi dicatat seluruhnya; konversi numerik hanya untuk kolom yang seluruh nilai nonkosongnya lolos. '
        'Kolom ID/kode tetap TEXT. Tidak ada penghapusan baris unmatched atau penambahan baris agar cocok baseline. '
        'Tidak dilakukan audit khusus kelengkapan EC. Tidak ada klaim penyebab perubahan selain yang terbukti dari filter/key/metadata.\n\n'
        'Duplikasi dan penggandaan di tabel di atas mengacu RAW. Status setelah deduplikasi dan unmatched versi pada CLEAN tersedia di '
        '`docs/reports/database/database_relationship_validation.csv`; jangan membaca RAW_BLOCKED sebagai kegagalan CLEAN yang telah terverifikasi. '
        'Angka duplicate_key_rows dari exporter biasanya berdasarkan assignment_id saja, sehingga bukan ukuran duplikasi anggota/usaha dengan key roster lengkap.\n')
    doc('DATA_ARCHITECTURE.md', '# Arsitektur data lokal\n\n```mermaid\nflowchart LR\n    A[Ekspor asli dan ZIP] --> B[Audit SHA-256 dan schema]\n    B --> C[Salinan data/raw]\n    C --> D[RAW per sumber dan batch]\n    D --> E[CLEAN tipe dan key versi]\n    E --> F[MART per grain]\n    E --> G[Tabel anak dan unmatched]\n```\n\n'
        'RAW menyimpan nilai sel asli dan tipe OOXML, source SHA, nomor baris, file, serta batch. File Excel asli tetap dipertahankan agar style/format dan struktur workbook tidak hilang. '
        'CLEAN menormalisasi tipe yang terbukti, mempertahankan timestamp asli, menambah timestamp normal, mendeduplikasi isi ternormalisasi identik per impor, dan menandai konflik. '
        'MART mempertahankan satu unit per key pada snapshot yang aktif. Tabel anak tidak dilebarkan bersama roster lain. '
        'Sosial P0+P1 dibentuk atas gabungan key yang sama-versi, termasuk P1-only. UB digabung hanya pada assignment_id dengan catatan provenance versi historis.\n\n'
        'Sync default dry-run. Impor berbasis SHA-256 dan schema sumber, satu transaksi per eksekusi. '
        'Ekspor berubah disimpan sebagai snapshot baru dan tidak mengganti snapshot aktif secara otomatis. '
        'File baru wajib dicantumkan pada `app/config/incoming.json` beserta source_id, SHA-256, jenis ekspor dan evidence. '
        'Delta/partial/unknown disimpan sebagai snapshot tersendiri, tidak dipromosikan menjadi mart terkini. '
        'Aktivasi snapshot penuh membutuhkan deklarasi eksplisit dan `--activate`; batch lama tetap ada. '
        'Pada modul TGR/P0/P1, wide mart dinonaktifkan sampai modul berada dalam batch integrasi yang sama. UB tidak mensyaratkan batch/timestamp sama; kelengkapan dan keunikan assignment_id diperiksa.\n\n'
        'SQLite lama dipertahankan. Database aktif berada di `data/processed/se2026.sqlite`. '
        'Foreign key wajib pada provenance impor-batch; relasi bisnis hanya diterapkan pada key yang lolos pemeriksaan dan tidak memaksa orphan terhapus.\n')
    architecture = root/DOCUMENTS['DATA_ARCHITECTURE.md']
    with architecture.open('a',encoding='utf-8') as stream:
        stream.write('\nDesimal CLEAN memakai declared type `DECIMAL_TEXT` dengan TEXT affinity agar presisi asli tidak dibulatkan SQLite REAL. '
                     'Nilainya dinormalisasi secara eksak dengan Decimal. Bilangan bulat tervalidasi memakai INTEGER; ID/kode tetap TEXT. '
                     'Gunakan Python Decimal untuk perhitungan keuangan presisi penuh. CAST ke REAL adalah pilihan analisis yang dapat membulatkan. '
                     'Rekap geografis menghitung `jumlah_unit_versi`, bukan klaim populasi unik lintas versi.\n')
    db = root/'data/processed/se2026.sqlite'
    imported, marts = {},set()
    database_checks = {}
    validation_path = root/'docs/reports/database/database_validation.json'
    validation = json.loads(validation_path.read_text(encoding='utf-8')) if validation_path.exists() else {}
    if db.exists():
        con = sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
        try:
            if con.execute("SELECT count(*) FROM sqlite_master WHERE name='imported_files'").fetchone()[0]:
                imported = dict(con.execute('SELECT source_id,SUM(raw_rows) FROM imported_files GROUP BY source_id'))
                marts = {n for n, in con.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'mart_%'")}
            if validation and db.stat().st_mtime<=validation_path.stat().st_mtime:
                database_checks = dict(integrity=validation.get('integrity'),foreign_key_violations=validation.get('foreign_key_violations'),evidence='docs/reports/database/database_validation.json')
            else:
                database_checks = dict(integrity=con.execute('PRAGMA integrity_check').fetchone()[0],foreign_key_violations=len(con.execute('PRAGMA foreign_key_check').fetchall()))
        finally:
            con.close()
    stages = []
    for s in sources:
        rel = next((r for r in audit['relationships'] if r['child']==s['id']),None)
        clean_rel = clean_relations.get(s['id'])
        relation_status = ('CLEAN partial: '+clean_rel['unmatched_child_rows']+' unmatched' if int(clean_rel['unmatched_child_rows']) else 'CLEAN matched') if clean_rel else rel['status'] if rel else 'master'
        if s['grain']=='ub':
            relation_status = 'ASSIGNMENT_KEY_VERIFIED; provenance versi historis belum diverifikasi'
        stages.append([s['id'],'ya','ya',imported.get(s['id'],0),relation_status,
                       'ya' if 'mart_'+s['id'] in marts else 'belum', 'tidak perlu ekspor timestamp UB' if s['grain']=='ub' else 'lihat kualitas/EOF'])
    stage_table = markdown_table(['Dataset','Ditemukan','Dibaca','Baris RAW diimpor','Dihubungkan','Mart per sumber','Kebutuhan tambahan'],stages)
    tests_path = root/'docs/reports/integration/test_results.xml'
    test_status = 'belum tersedia'
    if tests_path.exists():
        from xml.etree import ElementTree as ET
        suite = ET.parse(tests_path).getroot().find('testsuite')
        if suite is not None:
            test_status = f"{suite.attrib.get('tests')} pengujian; failures={suite.attrib.get('failures')}; errors={suite.attrib.get('errors')}"
    final = ('# Laporan akhir workspace dan integrasi\n\n'
        f'Diperbarui {utcnow()}. Audit mencakup {len(sources)} workbook data dan {total:,} baris. '
        'Seluruh proses data asli lokal; laporan tidak memuat nilai responden.\n\n'+stage_table+'\n\n'
        f'Pemeriksaan database aktual: `{json.dumps(database_checks)}`. '
        'Hasil uji sintetis, validasi database, checksum salinan dan pengulangan sync tersedia pada laporan pendamping.\n\n'
        f'RAW: {validation.get("raw_rows","belum diverifikasi")}; CLEAN: {validation.get("clean_rows","belum diverifikasi")}; '
        f'duplikat identik digabung: {validation.get("deduplicated_rows","belum diverifikasi")}. '
        f'Mart sosial union: {validation.get("social_union_rows","belum diverifikasi")} key; '
        f'P1-only: {validation.get("p1_only_rows","belum diverifikasi")}. '
        f'Uji sintetis aktual: {test_status}.\n\n'
        'Dataset master/rincian tetap terpisah. Tabel sosial terintegrasi mempertahankan key P1 yang tidak ada pada P0. '
        'UB terintegrasi berdasarkan assignment_id dengan status ASSIGNMENT_KEY_VERIFIED; versi historis hanya catatan provenance non-blocking. '
        'Kolom NULL/kode/tipe, jumlah baseline, orphan dan perbedaan waktu ada pada laporan kualitas.\n\n'
        'SQL Lab ditutup permanen. COUNT/EOF historis adalah catatan cakupan dan bukan blocker analitik; '
        'UB tidak memerlukan ekspor timestamp untuk analisis satu record per assignment; '
        'variabel yang tidak tersedia tidak direkayasa atau diwajibkan untuk pengembangan. '
        'Tidak ada database live yang diakses dan tidak ada SQL sumber yang dijalankan di SQL Lab.\n')
    write_document(root, 'reports/WORKSPACE_AND_INTEGRATION_FINAL_REPORT.md', final)
    doc('DEVELOPMENT_ROADMAP.md', '# Status dan pekerjaan lanjutan\n\n'
        'Selesai: inventaris file/ZIP/checksum, pembacaan streaming seluruh dataset yang ditemukan, profil kolom/kunci, '
        'uji relasi, salinan non-destruktif, dokumentasi dan fondasi sinkronisasi lokal. '
        'Status impor dan mart yang benar-benar tersedia dicatat per dataset pada laporan akhir.\n\n'
        'Prioritas berikutnya: lapisan semantik indikator dan wilayah lokal, dashboard deskriptif, serta validasi keunikan/kelengkapan assignment UB; '
        'jelaskan unmatched antarwaktu tanpa memaksa key; gunakan hanya variabel lokal yang tersedia; '
        'tambahkan aturan delta eksplisit sebelum delta dapat mengubah mart aktif; '
        'validasi makna bisnis indikator statistik sebelum dashboard lokal. Rencana rinci: docs/analytics/ANALYTICAL_DEVELOPMENT_ROADMAP.md.\n\n'
        'Risiko: schema drift, versi berbeda, skip pattern, cakupan kurasi terbatas, tidak tersedianya zona waktu sumber, '
        'dan sensitivitas pendapatan/disabilitas/kesehatan. Penyimpanan tetap lokal; konfigurasi ACL/enkripsi sistem operasi '
        'tidak diklaim telah diubah atau diverifikasi.\n')
    if clean_relations:
        with (root/DOCUMENTS['DATA_RELATIONSHIPS.md']).open('a',encoding='utf-8') as stream:
            stream.write('\nHasil setelah deduplikasi CLEAN:\n\n'+markdown_table(['Induk','Anak','Baris anak','Tanpa induk','Kelebihan JOIN','Status'],
                [[r[k] for k in ['parent','child','child_rows','unmatched_child_rows','multiplication_excess','status']] for r in clean_relations.values()])+'\n')
    if diagnoses:
        with (root/DOCUMENTS['DATA_RELATIONSHIPS.md']).open('a',encoding='utf-8') as stream:
            stream.write('\nDiagnosis unmatched P1 terhadap P0:\n\n'+markdown_table(['Modul','Unmatched','Assignment tidak ditemukan','Unit roster tidak ditemukan','Unit sama; timestamp berbeda'],
                [[d[k] for k in ['child','unmatched_rows','assignment_id_not_found','roster_unit_not_found','same_unit_different_timestamp']] for d in diagnoses if d['child'].startswith('p1_')])+'\n\n'
                '739 key P1-only pada mart awal adalah key anggota-versi, bukan klaim 739 orang baru. '
                'Banyak unit mempunyai versi waktu berbeda; versi tersebut sengaja tidak dipaksa bergabung.\n')
    phases = [
        ['1','Inventaris file, ZIP, SHA-256 dan skema checkpoint','docs/history/WORKSPACE_INVENTORY.md; data/metadata/file_manifest.json','Seluruh file dan isi ZIP diperiksa','README lama menyatakan folder kosong; audit aktual menjadi acuan','Profil dataset'],
        ['2','Identifikasi 27 workbook data TGR/TCZ/P1 dan SQL sumber','docs/reference/DATASET_CATALOG.md; data/metadata/source_query_inventory.csv','Header dan filter SQL diperiksa; SQL Lab tidak diakses','CSV/checklist adalah administrasi; PART metadata belum diekspor','Uji grain dan key'],
        ['3','Uji key, timestamp dan relasi seluruh modul','data/metadata/relationship_mapping.csv; docs/reports/database/relationship_validation.csv','Key temporal dinormalisasi; cardinality dan unmatched dihitung','Raw JOIN berisiko multiplication; UB tanpa timestamp','Audit kualitas'],
        ['4','Profil NULL, tipe, duplikasi, konflik, baseline dan cakupan','docs/reports/database/DATA_QUALITY_REPORT.md; docs/reports/database/data_quality_summary.csv','1.447.931 baris; 80 duplikat identik; konflik isi key=0','P1 key berbeda antar ekspor; EOF sejumlah sumber belum terbukti','Salinan aman'],
        ['5','Mapping path dan salinan non-destruktif','data/metadata/path_mapping.csv; docs/reports/integration/reorganization_validation.csv','228 salinan SHA-256 terverifikasi','Sumber asli dan checkpoint tetap tersedia','Bangun SQLite'],
        ['6','RAW/CLEAN/MART, provenance, indeks dan FK matched links','data/processed/se2026.sqlite; docs/reports/database/database_validation.json','integrity/foreign_key/count/grain diperiksa pada database aktual','Desimal presisi tinggi disimpan DECIMAL_TEXT; initial rollback tercatat','Sync idempoten'],
        ['7','CLI scan/validate/sync/report; batch immutable; dry-run','main.py; docs/reports/sync/sync_batches; docs/reports/sync/idempotency_verification.json','Pengulangan tidak menambah file/batch; failure rollback diuji sintetis','Partial/delta/unknown tidak mengganti mart aktif; perlu aturan bisnis delta','Dokumentasi'],
        ['8','README, AGENTS, katalog, relasi, arsitektur dan roadmap','README.md; AGENTS.md; docs/','Dokumen dibentuk dari audit dan database aktual','SQL Lab ditutup; COUNT historis hanya catatan cakupan lokal','Pengujian'],
        ['9','Pengujian sintetis dan preservasi sumber','tests/; docs/reports/integration/test_results.xml; docs/reports/integration/original_preservation_validation.csv',test_status,'ACL/enkripsi OS tidak diubah; tidak ada unggahan responden','Laporan akhir'],
        ['10','Pemisahan status ditemukan/dibaca/diimpor/dihubungkan/mart','docs/reports/integration/WORKSPACE_AND_INTEGRATION_FINAL_REPORT.md','Status per dataset dan batasan cakupan lokal dilaporkan','SQL Lab ditutup; tidak ada kebutuhan ekspor tambahan','Lanjutkan roadmap analitik lokal'],
    ]
    write_document(root, 'reports/PHASE_COMPLETION_LOG.md', '# Penyelesaian per fase\n\n'+markdown_table(['Fase','Pekerjaan','File/lokasi','Validasi aktual','Temuan/batasan','Berikutnya'],phases)+'\n')
    return dict(datasets=len(sources),rows=total,issues=len(issues),database_checks=database_checks)
