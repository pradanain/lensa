"""Checksum-verified copies only. Originals are never moved or removed."""
import json
import shutil
from pathlib import Path

from .layout import DOCUMENTS, write_document
from .common import dump, sha256, write_csv
from .scanner import load_config


def reorganize(root, apply=False):
    audit = json.loads((root / 'data/metadata/audit_results.json').read_text(encoding='utf-8'))
    manifest = json.loads((root / 'data/metadata/file_manifest.json').read_text(encoding='utf-8'))
    sources = {s['original']:s for s in load_config(root)}
    mapping = []
    for entry in manifest['files']:
        old = Path(entry['path'])
        if entry['path'] in sources:
            new, role = sources[entry['path']]['path'], 'raw_dataset'
        elif entry['extension'] == '.sql':
            parts = old.parts
            index = parts.index('01_SQL')
            new, role = 'app/sql/source_queries/' + Path(*parts[index+1:]).as_posix(), 'source_sql_unexecuted'
        elif old.name.endswith('.manifest.json'):
            new, role = 'data/metadata/source_metadata/' + old.as_posix(), 'export_metadata'
        elif entry['extension'] == '.zip':
            new, role = 'archive/source_packages/' + old.as_posix(), 'original_package'
        elif entry['extension'] in ('.sqlite','.sqlite3','.db'):
            new, role = 'archive/legacy_checkpoints/' + old.name, 'partial_export_checkpoint'
        else:
            new, role = 'archive/reference_material/' + old.as_posix(), 'administrative_reference'
        mapping.append(dict(old_path=old.as_posix(),new_path=new,sha256=entry['sha256'],role=role,operation='COPY_ONLY'))
    # Mapping and recovery plan are persisted before the first copy.
    write_csv(root / 'data/metadata/path_mapping.csv', mapping)
    (root / 'docs').mkdir(exist_ok=True)
    write_document(root, 'docs/WORKSPACE_REORGANIZATION_PLAN.md', '# Reorganisasi workspace\n\n'
        f'Audit selesai: {audit["generated_utc"]}. Mapping {len(mapping)} file tersedia di `data/metadata/path_mapping.csv`.\n\n'
        'Operasi hanya COPY. Data sumber tetap pada path semula; tidak ada rename, pemindahan, penghapusan, atau penimpaan. '
        'Setiap sumber dibandingkan dengan SHA-256 audit, disalin lewat file sementara, lalu SHA-256 salinan diverifikasi sebelum rename final. '
        'Target berbeda checksum memblokir proses. SQL sumber disalin apa adanya dan tidak dieksekusi terhadap SQL Lab.\n\n'
        'Pemulihan: gunakan sumber asli dan mapping. Salinan gagal tetap diabaikan oleh pipeline; file sementara memiliki akhiran `.copying`. '
        'Database baru terpisah dari checkpoint ekspor lama. Tidak perlu mengarsipkan atau menghapus sumber asli.\n\n'
        'Struktur aktif: `data/raw`, `data/incoming`, `data/staging`, `data/processed`, `data/exports`, '
        '`metadata`, `app/sql/source_queries`, `app/sql/validation`, `app/sql/transformations`, `app/sql/analytics`, `app/src/se2026`, `tests`, `docs`, `reports`, `config`, `archive`.\n')
    if not apply:
        return dict(planned=len(mapping),copied=0)
    results = []
    for row in mapping:
        source, target = root / row['old_path'], root / row['new_path']
        if sha256(source) != row['sha256']:
            raise ValueError('SOURCE_CHANGED_SINCE_AUDIT')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha256(target) != row['sha256']:
                raise ValueError('COPY_TARGET_CONFLICT')
            status = 'ALREADY_VERIFIED'
        else:
            temp = target.with_suffix(target.suffix + '.copying')
            shutil.copy2(source, temp)
            if sha256(temp) != row['sha256']:
                raise ValueError('COPY_CHECKSUM_FAILED')
            temp.replace(target)
            status = 'COPIED_VERIFIED'
        results.append(dict(**row,status=status))
    for name in ['data/incoming','data/staging','data/processed','data/exports','app/sql/validation','app/sql/transformations','app/sql/analytics','app/tests','docs/reports']:
        (root / name).mkdir(parents=True, exist_ok=True)
    write_csv(root / 'docs/reports/integration/reorganization_validation.csv', results)
    return dict(planned=len(mapping),verified=len(results))
