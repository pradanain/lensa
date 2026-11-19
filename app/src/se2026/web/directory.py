import hashlib
import json
import re
import threading
import time
from collections import defaultdict
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..common import q
from ..analytics.business_audit import register_population
from ..analytics.snapshot import file_stamp
from ..analytics.turnover import register_turnover, lookup as turnover_lookup, record as turnover_record
from .business_directory import enrich_businesses
from .family_directory import enrich_family_records
from .database import census_connection
from .sls_reference import SlsReference


class DirectoryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["dtd", "ub"] | None = None
    q: str = Field(default="", max_length=160)
    kecamatan: str = Field(default="", max_length=40)
    desa: str = Field(default="", max_length=40)
    sls: str = Field(default="", max_length=40)
    subsls: str = Field(default="", max_length=40)
    enumerated_only: bool = False
    qualified_only: bool = False
    status: str = Field(default="", max_length=100)
    kind: str = Field(default="", max_length=30)
    kbli_category: str = Field(default="", pattern=r"^[A-V]?$", max_length=1)
    kbli_prefix: str = Field(default="", pattern=r"^[0-9]{0,5}$", max_length=5)
    kbli_state: Literal["", "MISSING", "INVALID_FORMAT", "UNKNOWN_REFERENCE", "VALID"] = ""
    turnover_group: Literal["", "MIKRO", "KECIL", "MENENGAH", "BESAR", "UNAVAILABLE", "REVIEW"] = ""
    turnover_basis: Literal["", "REPORTED_ANNUAL", "ESTIMATE_MONTHLY_X12", "UNAVAILABLE"] = ""
    page: int = Field(default=1, ge=1, le=100000)
    page_size: int = Field(default=10, ge=1, le=100)
    sort: Literal["assignment_id", "title", "status", "kbli", "id", "business_priority", "family_priority"] = "id"
    direction: Literal["asc", "desc"] = "asc"


class DirectoryIndex:
    def __init__(self, settings, app_db, references):
        self.settings, self.db, self.references = settings, app_db, references
        self.sls_reference = SlsReference(settings.root, settings.sls_reference)
        self.lock = threading.Lock()
        self.signature = None
        self.verified_at = 0.0
        self.completeness_lock = threading.Lock()
        self.reference_stamp = file_stamp(self.sls_reference.path)
        self._set_order_reference()

    def _set_order_reference(self):
        self.order_reference = hashlib.sha256(json.dumps(
            [self.sls_reference.by_subsls, sorted(self.references.kbli)], sort_keys=True
        ).encode()).hexdigest()

    def completeness_scores(self, role, scope="businesses"):
        """Compatibility accessor; normal searches order by persisted integers."""
        self.ensure()
        self.ensure_order(scope)
        column = "score_admin" if role == "admin" else "score_viewer"
        with self.db.connection() as con:
            return {row[0]: row[1] for row in con.execute(
                "SELECT record_key," + column + " FROM directory_rows WHERE scope=?", (scope,))}

    @staticmethod
    def status_rank(scope, source, status):
        if scope == "businesses":
            if source == "dtd":
                return {"1": 0, "2": 1, "4": 2, "3": 3, "9": 4, "00": 5, "0": 5}.get(status, 6)
            return next((rank for prefix, rank in (("1.", 0), ("7.", 2), ("5.", 3), ("6.", 5))
                         if (status or "").startswith(prefix)), 6)
        codes = ("1", "2", "3", "4", "5", "6", "0") if scope == "families" else ("1", "5", "2", "3", "4", "6", "7")
        return codes.index(status) if status in codes else 7

    def ensure_order(self, scope):
        if scope not in ("businesses", "families", "members"):
            return
        expected_signature, reference = self.signature, self.order_reference
        token = f"{expected_signature}:{reference}:order-v2"
        key = "directory_order:" + scope
        with self.completeness_lock:
            with self.db.connection() as con:
                stored = con.execute("SELECT value FROM cache_meta WHERE key=?", (key,)).fetchone()
                if stored and stored[0] == token:
                    return
                rows = [
                    dict(row)
                    for row in con.execute(
                        "SELECT record_key,source,assignment_id,version,index1,title,desa,desa_label,"
                        "sls,subsls,kbli,kategori,status FROM directory_rows WHERE scope=?",
                        (scope,),
                    )
                ]
            # Enrich once, compute two independent visible-column scores. Hidden
            # values never contribute to Viewer order and are not copied to UI.
            rows = enrich_businesses(self.settings, rows, "admin") if scope == "businesses" else enrich_family_records(self.settings, rows, "admin", scope)
            turnover_states = turnover_lookup(self.settings.census_db) if scope == 'businesses' else None
            scores = []
            for row in rows:
                geo = self.sls_reference.describe(row["sls"], row["subsls"])

                def present(value):
                    return bool(str(value or "").strip())

                fields = [
                    present(row["title"]) and row["title"] not in ("Tanpa nama", "Usaha besar"),
                    present(row["desa_label"] or row["desa"]),
                    present(geo["sls_label"]),
                    bool(re.fullmatch(r"[0-9]{16}", row["subsls"] or "")),
                ]
                if scope == "businesses":
                    fields.extend([
                        present(row["family_head"] or row["person_in_charge"]),
                        row["kbli"] in self.references.kbli,
                        present(row["kategori"]),
                    ])
                    fields.append(turnover_record(turnover_states, row['source'], row['assignment_id'],
                        row['version'], row['index1']).group in ('MIKRO','KECIL','MENENGAH','BESAR'))
                elif scope == "members":
                    fields.extend(present(row[name]) for name in ("family_head", "member_number", "member_relationship", "member_gender", "member_age", "member_school", "member_diploma"))
                elif scope == "families":
                    fields.extend(present(row[name]) for name in ("building_number", "member_count", "business_count"))
                    fields.append(present(row["family_address"]))
                if scope in ("businesses", "families"):
                    fields.append(bool(row["map_coordinates"]))
                viewer_score = sum(fields)
                admin_score = viewer_score
                if scope == "members":
                    admin_score += present(row["member_nik"])
                scores.append((self.status_rank(scope, row["source"], row["status"]),
                               admin_score, viewer_score, row["record_key"]))
            with self.db.connection() as con:
                con.execute("BEGIN IMMEDIATE")
                signature = con.execute("SELECT value FROM cache_meta WHERE key='directory_signature'").fetchone()
                if (not signature or signature[0] != expected_signature
                    or self.source_signature() != expected_signature or self.order_reference != reference):
                    raise HTTPException(503, "DIRECTORY_SNAPSHOT_CHANGED")
                con.executemany("UPDATE directory_rows SET status_rank=?,score_admin=?,score_viewer=? WHERE record_key=?", scores)
                con.execute("INSERT INTO cache_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, token))

    def prepare_order(self):
        self.ensure()
        for scope in ("businesses", "families", "members"):
            self.ensure_order(scope)

    def ensure(self):
        reference_stamp = file_stamp(self.sls_reference.path)
        if reference_stamp != self.reference_stamp:
            with self.lock:
                self.sls_reference = SlsReference(self.settings.root, self.settings.sls_reference)
                self.reference_stamp = reference_stamp
                self._set_order_reference()
        signature = self.source_signature()
        if self.signature == signature:
            return
        with self.lock:
            with self.db.connection() as target:
                stored = target.execute(
                    "SELECT value FROM cache_meta WHERE key='directory_signature'"
                ).fetchone()
            if not stored or stored[0] != signature:
                self._build(signature)
            self.signature = signature
            self.verified_at = time.monotonic()

    def source_signature(self):
        stat = self.settings.census_db.stat()
        signature = f"{self.settings.census_db}:{stat.st_size}:{stat.st_mtime_ns}:directory-v7"
        wal = file_stamp(str(self.settings.census_db) + "-wal")
        if wal[1] is not None:
            signature += ":wal:" + hashlib.sha256(json.dumps(wal).encode()).hexdigest()
        return signature

    def _build(self, signature):
        with census_connection(self.settings) as source, self.db.connection() as target:
            target.execute("BEGIN IMMEDIATE")
            target.execute("DELETE FROM directory_rows")
            target.execute("DELETE FROM directory_fts")
            target.execute("DELETE FROM cache_meta WHERE key LIKE 'directory_order:%'")
            context = defaultdict(lambda: {"names": [], "title": None, "kind": "ASSIGNMENT", "version": None})
            geo = {}
            masters = {}
            for system, view in (("dtd", "mart_assignment_tgr"), ("ub", "mart_assignment_ub")):
                columns = [
                    "assignment_id",
                    "kode_kecamatan",
                    "kode_desa",
                    "kode_sls",
                    "kode_subsls",
                    "kecamatan",
                    "desa_kelurahan",
                    "status_assignment",
                    "status_kuesioner",
                ]
                masters[system] = [
                    dict(r)
                    for r in source.execute("SELECT " + ",".join(map(q, columns)) + " FROM " + q(view))
                ]
                for row in masters[system]:
                    geo[(system, row["assignment_id"])] = row

            records, search_records = [], []
            row_number = 0

            def flush():
                target.executemany(
                    "INSERT INTO directory_rows(id,scope,source,record_key,assignment_id,version,index1,title,status,status_label,kecamatan,desa,sls,subsls,kecamatan_label,desa_label,kbli,kategori,kind,kbli_state) VALUES("
                    + ",".join("?" for _ in range(20)) + ")", records)
                target.executemany("INSERT INTO directory_fts(rowid,search_text,restricted_text) VALUES(?,?,?)", search_records)
                records.clear()
                search_records.clear()

            def add(
                scope,
                system,
                row,
                title,
                status="",
                status_label="",
                kbli="",
                category="",
                kind="",
                restricted="",
            ):
                nonlocal row_number
                row_number += 1
                aid = str(row["assignment_id"])
                version = row.get("__version_normalized")
                index = row.get("index1")
                category_match = re.fullmatch(r"([A-V])(?:[.\s].*)?", str(category or "").strip())
                category = category_match[1] if category_match else category
                key = hashlib.sha256(
                    json.dumps([scope, system, aid, version, index], separators=(",", ":")).encode()
                ).hexdigest()
                g = geo.get((system, aid), {})
                record = (
                    scope,
                    system,
                    key,
                    aid,
                    version,
                    index,
                    title,
                    status,
                    status_label,
                    g.get("kode_kecamatan"),
                    g.get("kode_desa"),
                    g.get("kode_sls"),
                    g.get("kode_subsls"),
                    g.get("kecamatan"),
                    g.get("desa_kelurahan"),
                    kbli,
                    category,
                    kind,
                    self.references.kbli_state(kbli),
                )
                records.append((row_number, *record))
                search = " ".join(str(v or "") for v in [aid, title, kbli, *row.get("search_names", [])])
                search_records.append((row_number, search, restricted))
                if len(records) >= 1000:
                    flush()

            family_numbers = defaultdict(list)
            for family in source.execute("SELECT assignment_id,__version_normalized,no_kk FROM mart_keluarga"):
                family_numbers[(family["assignment_id"], family["__version_normalized"])].append(family["no_kk"])

            definitions = [
                (
                    "families",
                    "mart_keluarga",
                    [
                        "assignment_id",
                        "__version_normalized",
                        "nama_kk",
                        "kode_keberadaan_keluarga",
                        "keberadaan_keluarga",
                    ],
                    "nama_kk",
                    "kode_keberadaan_keluarga",
                    "keberadaan_keluarga",
                    "KELUARGA",
                ),
                (
                    "businesses",
                    "mart_usaha",
                    [
                        "assignment_id",
                        "__version_normalized",
                        "index1",
                        "nama_usaha",
                        "kode_keberadaan_usaha",
                        "keberadaan_usaha",
                        "kbli",
                        "kategori",
                    ],
                    "nama_usaha",
                    "kode_keberadaan_usaha",
                    "keberadaan_usaha",
                    "USAHA",
                ),
                (
                    "members",
                    "mart_anggota",
                    [
                        "assignment_id",
                        "__version_normalized",
                        "index1",
                        "nama_anggota",
                        "nik_anggota",
                        "kode_keberadaan_anggota",
                        "keberadaan_anggota",
                    ],
                    "nama_anggota",
                    "kode_keberadaan_anggota",
                    "keberadaan_anggota",
                    "ANGGOTA",
                ),
            ]
            for scope, view, columns, title_col, status_col, status_label, kind in definitions:
                for item in source.execute("SELECT " + ",".join(map(q, columns)) + " FROM " + q(view)):
                    row = dict(item)
                    numbers = family_numbers[(row["assignment_id"], row["__version_normalized"])]
                    family_kk = numbers[0] if len(numbers) == 1 else None
                    add(
                        scope,
                        "dtd",
                        row,
                        row[title_col] or "Tanpa nama",
                        row[status_col],
                        row[status_label],
                        row.get("kbli", ""),
                        row.get("kategori", ""),
                        kind,
                        restricted=" ".join(str(value or "") for value in [family_kk, row.get("nik_anggota")]) if scope in ("families", "members") else "",
                    )
                    if scope != "members":
                        c = context[row["assignment_id"]]
                        c["names"].append(row[title_col] or "")
                        # Classification follows source presence, including a
                        # family whose display name is blank.
                        if scope == "families" or c["kind"] == "ASSIGNMENT":
                            c["kind"] = kind
                        if not c["title"]:
                            c.update(title=row[title_col], version=row["__version_normalized"])
            for item in source.execute(
                "SELECT assignment_id,__version_normalized,nama_bangunan_usaha FROM mart_bku"
            ):
                row = dict(item)
                c = context[row["assignment_id"]]
                c["kind"] = "KELUARGA_BKU" if c["kind"].startswith("KELUARGA") else "BKU"
                c["names"].append(row["nama_bangunan_usaha"] or "")
                if not c["title"]:
                    c.update(title=row["nama_bangunan_usaha"], version=row["__version_normalized"])
            for master in masters["dtd"]:
                c = context[master["assignment_id"]]
                add(
                    "assignments",
                    "dtd",
                    # A master row has assignment grain. The questionnaire
                    # chooses its supported root version; child-row iteration
                    # order must not silently select an older questionnaire.
                    {**master, "search_names": c["names"]},
                    c["title"] or "Assignment DTD",
                    master["status_assignment"],
                    master["status_kuesioner"],
                    kind=c["kind"],
                )
            ub_names = {}
            for item in source.execute(
                "SELECT assignment_id,nama_usaha,status_keberadaan,kbli_akhir,kategori_kbli,nib FROM mart_ub_a"
            ):
                row = dict(item)
                ub_names[row["assignment_id"]] = row
                add(
                    "businesses",
                    "ub",
                    row,
                    row["nama_usaha"] or "Usaha besar",
                    row["status_keberadaan"],
                    row["status_keberadaan"],
                    row["kbli_akhir"],
                    row["kategori_kbli"],
                    "UB",
                    row["nib"] or "",
                )
            for master in masters["ub"]:
                row = ub_names.get(master["assignment_id"], {})
                add(
                    "assignments",
                    "ub",
                    master,
                    row.get("nama_usaha") or "Assignment UB",
                    master["status_assignment"],
                    row.get("status_keberadaan", ""),
                    row.get("kbli_akhir", ""),
                    row.get("kategori_kbli", ""),
                    "UB",
                    row.get("nib") or "",
                )
            flush()
            if self.source_signature() != signature:
                raise HTTPException(503, "DIRECTORY_SNAPSHOT_CHANGED")
            target.execute(
                "INSERT INTO cache_meta VALUES('directory_signature',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (signature,),
            )
            target.execute(
                "INSERT INTO cache_meta VALUES('directory_built_at',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(int(time.time())),),
            )

    @staticmethod
    def where(scope, payload, role):
        if scope not in ("assignments", "businesses", "families", "members"):
            raise HTTPException(404, "DIRECTORY_NOT_FOUND")
        clauses, bindings = ["d.scope=?"], [scope]
        if payload.qualified_only and scope == 'businesses':
            clauses.append('AUDIT_QUALIFIED(d.source,d.assignment_id,d.version,d.index1)=1')
        if (payload.enumerated_only or payload.turnover_group or payload.turnover_basis) and scope == "businesses":
            clauses.append(
                "((d.source='dtd' AND d.status IN ('1','2')) OR "
                "(d.source='ub' AND d.status='1. Ditemukan dan masih aktif')) "
                "AND EXISTS (SELECT 1 FROM directory_rows a INDEXED BY directory_assignment WHERE a.scope='assignments' "
                "AND a.source=d.source AND a.assignment_id=d.assignment_id "
                "AND a.status IN ('APPROVED BY Pengawas','COMPLETED BY Admin Kabupaten'))"
            )
        for name, field in (
            ("source", "source"),
            ("kecamatan", "kecamatan"),
            ("desa", "desa"),
            ("sls", "sls"),
            ("subsls", "subsls"),
            ("status", "status"),
            ("kind", "kind"),
            ("kbli_category", "kategori"),
            ("kbli_state", "kbli_state"),
        ):
            value = getattr(payload, name)
            if value:
                clauses.append("d." + q(field) + "=?")
                bindings.append(value)
        if payload.kbli_prefix:
            clauses.append("d.kbli LIKE ?")
            bindings.append(payload.kbli_prefix + "%")
        if payload.turnover_group or payload.turnover_basis:
            if scope != 'businesses':
                raise HTTPException(422, 'TURNOVER_FILTER_BUSINESSES_ONLY')
            for name, function in [('turnover_group','TURNOVER_GROUP'),('turnover_basis','TURNOVER_BASIS')]:
                value = getattr(payload, name)
                if value:
                    clauses.append(function+'(d.source,d.assignment_id,d.version,d.index1)=?')
                    bindings.append(value)
        if payload.q.strip():
            words = re.findall(r"\w+", payload.q, flags=re.UNICODE)[:12]
            if not words:
                clauses.append("0=1")
            else:
                column = "{search_text restricted_text}" if role == "admin" else "search_text"
                terms = " AND ".join('"' + word.replace('"', '""') + '"*' for word in words)
                clauses.append("d.id IN (SELECT rowid FROM directory_fts WHERE directory_fts MATCH ?)")
                bindings.append(column + " : (" + terms + ")")
        return " AND ".join(clauses), bindings

    def search(self, scope, payload, role, *, all_rows=False):
        self.ensure()
        where, values = self.where(scope, payload, role)
        order = "d." + q(payload.sort) + (" DESC" if payload.direction == "desc" else " ASC") + ",d.id ASC"
        priority = ((scope == "businesses" and payload.sort in ("id", "business_priority"))
                    or (scope in ("families", "members") and payload.sort in ("id", "family_priority")))
        if priority:
            self.ensure_order(scope)
            column = "score_admin" if role == "admin" else "score_viewer"
            order = (
                "d.status_rank ASC,d." + column + " DESC,"
                "d.title COLLATE NOCASE ASC,d.assignment_id ASC,d.version ASC,d.index1 ASC,d.id ASC"
            )
        elif payload.sort in ("business_priority", "family_priority"):
            order = "d.id ASC"
        with self.db.connection() as con:
            con.execute("BEGIN")
            active = con.execute("SELECT value FROM cache_meta WHERE key='directory_signature'").fetchone()
            if not active or active[0] != self.signature:
                raise HTTPException(503, "DIRECTORY_SNAPSHOT_CHANGED")
            if payload.turnover_group or payload.turnover_basis:
                register_turnover(con, self.settings.census_db)
            if payload.qualified_only and scope == 'businesses':
                register_population(con, self.settings.census_db, self.settings.root)
            total = con.execute("SELECT COUNT(*) FROM directory_rows d WHERE " + where, values).fetchone()[0]
            rows = con.execute(
                "SELECT d.record_key,d.source,d.assignment_id,d.version,d.index1,d.title,d.status,d.status_label,d.kecamatan,d.desa,d.sls,d.subsls,d.kecamatan_label,d.desa_label,d.kbli,d.kategori,d.kind,d.kbli_state FROM directory_rows d WHERE "
                + where
                + " ORDER BY "
                + order
                + ("" if all_rows else " LIMIT ? OFFSET ?"),
                values if all_rows else [*values, payload.page_size, (payload.page - 1) * payload.page_size],
            ).fetchall()
        result_rows = [dict(r) | self.sls_reference.describe(r["sls"], r["subsls"]) for r in rows]
        if scope == "businesses":
            for row in result_rows:
                row["kbli_title"] = self.references.hierarchy.nodes.get(str(row["kbli"] or "").strip(), {}).get("title")
            result_rows = enrich_businesses(self.settings, result_rows, role)
            states = turnover_lookup(self.settings.census_db)
            for row in result_rows:
                row['turnover'] = turnover_record(states, row['source'], row['assignment_id'],
                    row['version'], row['index1']).public(sensitive=True)
        elif scope in ("families", "members"):
            result_rows = enrich_family_records(self.settings, result_rows, role, scope)
        return dict(
            rows=result_rows,
            total=total,
            page=payload.page,
            page_size=payload.page_size,
            pages=max(1, (total + payload.page_size - 1) // payload.page_size),
            grain={
                "assignments": "assignment_id per source",
                "families": "assignment_id + version",
                "members": "assignment_id + version + index1",
                "businesses": "DTD assignment + version + index1; UB assignment_id",
            }[scope],
            search_in_url=False,
        )

    def aggregate_counts(self, scope, source, field, qualified_only=False, enumerated_only=False,
                         turnover_group='', turnover_basis='', kecamatan='', desa='', sls='', subsls=''):
        self.ensure()
        if field not in ("kbli", "kategori", "kbli_state", "kecamatan", "status"):
            raise HTTPException(422, "DIMENSION_NOT_ALLOWED")
        with self.db.connection() as con:
            where, bindings = self.where(scope, DirectoryQuery(source=source, qualified_only=qualified_only,
                enumerated_only=enumerated_only, turnover_group=turnover_group, turnover_basis=turnover_basis,
                kecamatan=kecamatan, desa=desa, sls=sls, subsls=subsls), 'aggregate_viewer')
            if turnover_group or turnover_basis:
                register_turnover(con, self.settings.census_db)
            if qualified_only and scope == 'businesses':
                register_population(con, self.settings.census_db, self.settings.root)
            return [
                dict(row)
                for row in con.execute(
                    "SELECT "
                    + 'd.' + q(field)
                    + " AS code,COUNT(*) AS units FROM directory_rows d WHERE " + where + " GROUP BY d."
                    + q(field),
                    bindings,
                )
            ]

    def status_options(self, scope, source):
        self.ensure()
        with self.db.connection() as con:
            rows = con.execute(
                "SELECT status,status_label FROM directory_rows WHERE scope=? AND source=? "
                "AND status IS NOT NULL GROUP BY status,status_label ORDER BY status,status_label",
                (scope, source),
            ).fetchall()
        labels = defaultdict(set)
        for row in rows:
            code = row["status"]
            # Assignment status and questionnaire presence describe different things.
            raw = code if scope == "assignments" else row["status_label"] or code
            label = re.sub(r"^\s*\d+\s*[.)\-:]\s*", "", str(raw)).strip()
            if not label or label.isdigit():
                label = "Label belum tersedia"
            labels[code].add(label)
        return [dict(code=code, label=" / ".join(sorted(values))) for code, values in labels.items()]

    def geography(self, source, level, parent=""):
        self.ensure()
        fields = {
            "kecamatan": ("kecamatan", "kecamatan_label", None),
            "desa": ("desa", "desa_label", "kecamatan"),
            "sls": ("sls", "sls", "desa"),
            "subsls": ("subsls", "subsls", "sls"),
        }
        if source not in ("dtd", "ub") or level not in fields:
            raise HTTPException(422, "GEOGRAPHY_NOT_ALLOWED")
        code, label, parent_col = fields[level]
        where, values = "scope='assignments' AND source=?", [source]
        if parent and parent_col:
            where += " AND " + q(parent_col) + "=?"
            values.append(parent)
        with self.db.connection() as con:
            rows = [
                dict(row)
                for row in con.execute(
                    "SELECT "
                    + q(code)
                    + " AS code,MAX("
                    + q(label)
                    + ") AS label FROM directory_rows WHERE "
                    + where
                    + " GROUP BY "
                    + q(code)
                    + " ORDER BY "
                    + q(code),
                    values,
                )
            ]
        if level in ("sls", "subsls"):
            rows = [row for row in rows if row["code"]]
            for row in rows:
                row["label"] = self.sls_reference.choice_label(level, row["code"])
        return rows
