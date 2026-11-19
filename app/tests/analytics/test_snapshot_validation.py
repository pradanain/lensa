import json
import shutil
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from se2026.analytics import Analytics
from se2026.analytics.registry import AnalyticsError


def test_verified_grain_is_reused_but_changed_snapshot_is_checked(analytical_db):
    calls = []
    validate = Analytics._validate_source

    def checked(self, source):
        calls.append(source)
        return validate(self, source)

    with patch.object(Analytics, '_validate_source', checked):
        for _ in range(2):
            with Analytics(analytical_db) as api:
                api.query('anggota.count')
        assert calls == ['anggota']
        with sqlite3.connect(analytical_db) as con:
            con.execute('INSERT INTO mart_anggota SELECT * FROM mart_anggota LIMIT 1')
        # A successful old check cannot mask a duplicate in a new snapshot.
        for _ in range(2):
            with Analytics(analytical_db) as api:
                with pytest.raises(AnalyticsError, match='SOURCE_GRAIN_NOT_UNIQUE'):
                    api.query('anggota.count')
        assert calls == ['anggota', 'anggota', 'anggota']


def test_wal_commit_invalidates_validation_even_without_checkpoint(analytical_db):
    with sqlite3.connect(analytical_db) as writer:
        writer.execute('PRAGMA journal_mode=WAL')
        with Analytics(analytical_db) as api:
            api.query('anggota.count')
        writer.execute('INSERT INTO mart_anggota SELECT * FROM mart_anggota LIMIT 1')
        writer.commit()
        with Analytics(analytical_db) as api:
            with pytest.raises(AnalyticsError, match='SOURCE_GRAIN_NOT_UNIQUE'):
                api.query('anggota.count')


def test_definition_change_invalidates_successful_validation(analytical_db, tmp_path):
    ROOT = Path(__file__).resolve().parents[3]
    root = tmp_path / 'definitions'
    for folder in ('app/config/analytics', 'app/sql/analytics'):
        shutil.copytree(ROOT / folder, root / folder)
    with Analytics(analytical_db, root) as api:
        api.query('anggota.count')
    source_file = root / 'app/config/analytics/sources.json'
    sources = json.loads(source_file.read_text(encoding='utf-8'))
    sources['anggota']['grain_key'].append('nonexistent_key')
    source_file.write_text(json.dumps(sources), encoding='utf-8')
    with Analytics(analytical_db, root) as api:
        with pytest.raises(AnalyticsError, match='SOURCE_SCHEMA_MISMATCH'):
            api.query('anggota.count')
