"""Read-only live validation; reports counts/statuses only, never respondent values."""

import json
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app/src"))


def main():
    from se2026.analytics import Analytics
    from se2026.common import q, sha256
    from se2026.web.database import census_connection
    from se2026.web.directory import DirectoryQuery
    from se2026.web.main import create_app
    from se2026.web.settings import Settings

    settings = Settings()
    output = ROOT / "docs/reports/app/live_validation.json"
    before = json.loads((output.parent / "baseline_before.json").read_text(encoding="utf-8"))
    initial_hash = sha256(settings.census_db)
    assert initial_hash == before["database_sha256"], "BASELINE_HASH_DIFFERENT"
    sources = json.loads((ROOT / "app/config/sources.json").read_text(encoding="utf-8"))["sources"]
    start = time.perf_counter()
    with census_connection(settings) as con:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        fk = len(con.execute("PRAGMA foreign_key_check").fetchall())
        counts = {
            layer: {
                s["id"]: con.execute("SELECT COUNT(*) FROM " + q(layer + "_" + s["id"])).fetchone()[0]
                for s in sources
            }
            for layer in ("raw", "clean", "mart")
        }
        ub_ids = {}
        for name in ["assignment_ub", "ub_a", "ub_b", "ub_c", "ub_integrated"]:
            rows = con.execute("SELECT assignment_id FROM " + q("mart_" + name)).fetchall()
            ub_ids[name] = [r[0] for r in rows]
        target = set(ub_ids["assignment_ub"])
        ub_check = {
            name: dict(
                rows=len(ids),
                unique=len(set(ids)),
                null_ids=sum(v is None for v in ids),
                missing_ids=len(target - set(ids)),
                extra_ids=len(set(ids) - target),
            )
            for name, ids in ub_ids.items()
        }
        complete = con.execute(
            "SELECT COUNT(*) FROM mart_ub_integrated WHERE has_assignment_ub=1 AND has_ub_a=1 AND has_ub_b=1 AND has_ub_c=1"
        ).fetchone()[0]
        # IDs remain in process memory only. No values enter the report.
        dtd_ids = [r[0] for r in con.execute("SELECT assignment_id FROM mart_assignment_tgr LIMIT 20")]
    integrity_seconds = time.perf_counter() - start
    assert integrity == "ok" and fk == 0
    assert complete == 226 and all(
        r["rows"] == r["unique"] == 226 and not r["null_ids"] and not r["missing_ids"] and not r["extra_ids"]
        for r in ub_check.values()
    )
    app = create_app(settings)
    start = time.perf_counter()
    app.state.directory.ensure()
    index_seconds = time.perf_counter() - start

    def timed(label, operation, runs=3):
        durations = []
        for _ in range(runs):
            tick = time.perf_counter()
            operation()
            durations.append(round((time.perf_counter() - tick) * 1000, 2))
        return dict(operation=label, runs=runs, median_ms=statistics.median(durations), max_ms=max(durations))

    benchmarks = [
        timed(
            "DTD first page, cached directory",
            lambda: app.state.directory.search("assignments", DirectoryQuery(source="dtd"), "admin"),
        ),
        timed(
            "UB first page, cached directory",
            lambda: app.state.directory.search("assignments", DirectoryQuery(source="ub"), "admin"),
        ),
        timed(
            "Empty synthetic search on live local FTS",
            lambda: app.state.directory.search(
                "businesses", DirectoryQuery(q="SYNTHETIC_NO_RESPONDENT_EXPECTED_902731"), "admin"
            ),
        ),
        timed(
            "KBLI leading-zero prefix",
            lambda: app.state.directory.search("businesses", DirectoryQuery(kbli_prefix="01"), "admin"),
        ),
    ]
    statuses = Counter()
    start = time.perf_counter()
    for aid in ub_ids["assignment_ub"]:
        form = app.state.questionnaires.get("ub", aid, "analyst_detail")
        assert (
            len(form["sections"]) == 5
            and form["questionnaire_version_status"] == "QUESTIONNAIRE_VERSION_NOT_VERIFIED"
        )
        statuses.update(f["status"] for s in form["sections"] for f in s["questions"])
    ub_seconds = time.perf_counter() - start
    start = time.perf_counter()
    for aid in dtd_ids:
        form = app.state.questionnaires.get("dtd", aid, "analyst_detail")
        assert len(form["sections"]) == 11
    dtd_seconds = time.perf_counter() - start
    with Analytics(settings.census_db, settings.root) as semantic:
        benchmarks.append(
            timed(
                "Established public semantic summary, seven counts",
                lambda: [
                    semantic.query(m)
                    for m in [
                        "assignment_tgr.count",
                        "assignment_ub.count",
                        "keluarga.count",
                        "anggota.count",
                        "bku.count",
                        "usaha.count",
                        "ub.count",
                    ]
                ],
            )
        )
    with app.state.app_db.connection() as con:
        directory_counts = [
            dict(r)
            for r in con.execute(
                "SELECT scope,source,COUNT(*) AS records FROM directory_rows GROUP BY scope,source"
            )
        ]
        user_count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    manifest = json.loads((ROOT / "data/metadata/file_manifest.json").read_text(encoding="utf-8"))
    original_files_ok = sum(sha256(ROOT / f["path"]) == f["sha256"] for f in manifest["files"])
    assert original_files_ok == len(manifest["files"])
    raw_ok = sum(sha256(ROOT / s["path"]) == sha256(ROOT / s["original"]) for s in sources)
    assert raw_ok == len(sources)
    backup = ROOT / before["backup_root"] / "before"
    protected = [
        p
        for area in ["src", "sql", "config", "scripts", "tests"]
        for p in (backup / "app" / area).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".md")
    ]
    preserved = sum(
        (ROOT / p.relative_to(backup)).is_file() and sha256(p) == sha256(ROOT / p.relative_to(backup))
        for p in protected
    )
    assert preserved == len(protected), "EXISTING_APP_SOURCE_CHANGED"
    final_hash = sha256(settings.census_db)
    assert initial_hash == final_hash
    report = dict(
        generated_utc=datetime.now(timezone.utc).isoformat(),
        census_sha256_before=initial_hash,
        census_sha256_after=final_hash,
        census_unchanged=True,
        integrity=integrity,
        foreign_key_violations=fk,
        integrity_seconds=round(integrity_seconds, 2),
        datasets=len(sources),
        layer_counts=counts,
        layer_totals={k: sum(v.values()) for k, v in counts.items()},
        ub_keys=ub_check,
        ub_complete=complete,
        ub_rendered=226,
        ub_render_seconds=round(ub_seconds, 2),
        ub_field_status_counts=dict(statuses),
        dtd_rendered=len(dtd_ids),
        dtd_render_seconds=round(dtd_seconds, 2),
        directory_counts=directory_counts,
        index_ensure_seconds=round(index_seconds, 2),
        benchmarks=benchmarks,
        original_files_verified=original_files_ok,
        raw_copies_verified=raw_ok,
        existing_app_code_config_files_unchanged=preserved,
        local_users_at_validation=user_count,
        no_real_account_created=True,
        notes=[
            "Measurements are local warm runs, not concurrent-load or production benchmarks.",
            "Only aggregate statuses/counts are persisted; no respondent identifiers or answers.",
            "Questionnaire smoke validation reads answers in memory; mapping/evidence and exact-key semantics are separately covered by synthetic tests.",
        ],
    )
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Live validation passed; aggregate evidence: docs/reports/app/live_validation.json")


if __name__ == "__main__":
    main()
