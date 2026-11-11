import hashlib
import json
import re
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException

from ..analytics.numeric import parse_decimal
from ..common import q, timestamp
from .database import census_connection

STATUSES = {
    "ANSWERED",
    "BLANK_OR_MISSING",
    "SKIPPED_NOT_APPLICABLE",
    "NOT_EXPORTED",
    "UNMATCHED_VERSION",
    "UNVERIFIED_MAPPING",
    "RESTRICTED",
}


def present(value):
    return value is not None and str(value).strip() != ""


def choice_code(value):
    if not present(value):
        return None
    match = re.match(r"^([0-9]+)(?:[.\s]|$)", str(value).strip())
    return match[1] if match else str(value).strip()


class Questionnaires:
    def __init__(self, settings, references):
        self.settings, self.references = settings, references
        folder = settings.root / "app/config/questionnaires"
        self.forms = {
            name: json.loads((folder / (name + ".json")).read_text(encoding="utf-8"))
            for name in ("dtd", "ub")
        }
        self.sources = {
            s["id"]: s
            for s in json.loads((settings.root / "app/config/sources.json").read_text(encoding="utf-8"))[
                "sources"
            ]
        }
        self.schemas = {}
        verified = {}
        with census_connection(settings) as con:
            for sid in self.sources:
                self.schemas[sid] = {r[1] for r in con.execute("PRAGMA table_info(" + q("mart_" + sid) + ")")}
            for form in self.forms.values():
                ids = set()
                for section in form["sections"]:
                    for field in section["questions"]:
                        if field["question_id"] in ids:
                            raise ValueError("DUPLICATE_QUESTION_ID")
                        ids.add(field["question_id"])
                        if field["mapping_status"] != "VERIFIED":
                            continue
                        sid = field["source_object"].removeprefix("mart_")
                        if sid not in self.schemas or field["source_field"] not in self.schemas[sid]:
                            raise ValueError("QUESTIONNAIRE_SCHEMA_DRIFT")
                        if field.get("label_field") and field["label_field"] not in self.schemas[sid]:
                            raise ValueError("QUESTIONNAIRE_LABEL_DRIFT")
                        evidence = field["evidence"]
                        path = settings.root / evidence["sql_path"]
                        if evidence["sql_path"] not in verified:
                            verified[evidence["sql_path"]] = hashlib.sha256(path.read_bytes()).hexdigest()
                        if verified[evidence["sql_path"]] != evidence["sql_sha256"]:
                            raise ValueError("QUESTIONNAIRE_SQL_EVIDENCE_DRIFT")

    def schema_summary(self):
        return {
            name: dict(
                sections=len(form["sections"]),
                questions=sum(len(s["questions"]) for s in form["sections"]),
                verified=sum(
                    f["mapping_status"] == "VERIFIED" for s in form["sections"] for f in s["questions"]
                ),
                reference=form["reference"],
            )
            for name, form in self.forms.items()
        }

    def _columns(self, name, sensitive):
        columns = {"assignment_id", "__version_normalized", "__source_sha256", "__batch_id"}
        columns.update(
            c
            for c in ("index1", "index_meteran", "index_usaha", "index_kantor_unit")
            if c in self.schemas[name]
        )
        roster_label = {
            "anggota": "nama_anggota",
            "sosial_p0": "nama_anggota",
            "usaha": "nama_usaha",
            "kantor_unit": "nama_kantor_unit",
        }.get(name)
        if roster_label:
            columns.add(roster_label)
        for form in self.forms.values():
            for section in form["sections"]:
                for field in section["questions"]:
                    if (
                        field["mapping_status"] == "VERIFIED"
                        and field["source_object"] == "mart_" + name
                        and (sensitive or not field.get("sensitive"))
                    ):
                        columns.add(field["source_field"])
                        if field.get("label_field"):
                            columns.add(field["label_field"])
                    rule = field.get("visibility_rule")
                    if rule and rule["source"] == name:
                        columns.add(rule["field"])
        # Source metadata is optional in synthetic/alternative schemas; answer/key
        # references were validated above and never silently substituted.
        return sorted(columns & self.schemas[name])

    def get(
        self, system, assignment_id, role, version=None, business=None, member=None, meter=None, office=None
    ):
        if system not in self.forms or len(assignment_id) > 100:
            raise HTTPException(404, "QUESTIONNAIRE_NOT_FOUND")
        can_sensitive = role == "admin"
        form = self.forms[system]
        source_ids = [
            sid
            for sid, s in self.sources.items()
            if (s["system"] == "TCZ") == (system == "ub") and s["grain"] != "assignment"
        ]
        with census_connection(self.settings) as con:
            master = con.execute(
                "SELECT assignment_id,status_assignment,status_kuesioner,kecamatan,desa_kelurahan,kode_kecamatan,kode_desa,versi_root_terbaru FROM "
                + q("mart_assignment_ub" if system == "ub" else "mart_assignment_tgr")
                + " WHERE assignment_id=?",
                (assignment_id,),
            ).fetchone()
            if not master:
                raise HTTPException(404, "QUESTIONNAIRE_NOT_FOUND")
            versions = set()
            if system == "dtd":
                for sid in source_ids:
                    for row in con.execute(
                        "SELECT __version_normalized FROM "
                        + q("mart_" + sid)
                        + " WHERE assignment_id=? GROUP BY __version_normalized",
                        (assignment_id,),
                    ):
                        if present(row[0]):
                            versions.add(row[0])
                if version and version not in versions:
                    raise HTTPException(422, "QUESTIONNAIRE_VERSION_NOT_AVAILABLE")
                preferred = timestamp(master["versi_root_terbaru"]) if master["versi_root_terbaru"] else None
                version = version or (
                    preferred
                    if preferred in versions
                    else sorted(versions, reverse=True)[0]
                    if versions
                    else None
                )
            rows, other_versions, truncated, other_keys = {}, set(), [], {}
            for sid in source_ids:
                columns = self._columns(sid, can_sensitive)
                sql = (
                    "SELECT "
                    + ",".join(map(q, columns))
                    + " FROM "
                    + q("mart_" + sid)
                    + " WHERE assignment_id=?"
                )
                bindings = [assignment_id]
                if system == "dtd":
                    sql += " AND __version_normalized=?"
                    bindings.append(version)
                found = [dict(r) for r in con.execute(sql + " LIMIT 1001", bindings)]
                if len(found) > 1000:
                    truncated.append(sid)
                    found = found[:1000]
                rows[sid] = found
                if system == "dtd":
                    key_columns = [
                        c
                        for c in ("index1", "index_meteran", "index_usaha", "index_kantor_unit")
                        if c in self.schemas[sid]
                    ]
                    other = [
                        dict(r)
                        for r in con.execute(
                            "SELECT "
                            + ",".join(map(q, ["__version_normalized", *key_columns]))
                            + " FROM "
                            + q("mart_" + sid)
                            + " WHERE assignment_id=? AND __version_normalized<>? LIMIT 1001",
                            (assignment_id, version),
                        )
                    ]
                    other_keys[sid] = (key_columns, other)
                    if other:
                        other_versions.add(sid)
        rosters = {"businesses": {}, "members": {}, "meters": {}, "offices": {}}
        for sid in ["anggota", "sosial_p0", "p1_pekerjaan", "p1_disabilitas", "p1_kronis_a", "p1_kronis_b"]:
            for row in rows.get(sid, []):
                key = str(row["index1"])
                rosters["members"].setdefault(
                    key, dict(index=key, label=row.get("nama_anggota") or "Anggota " + key)
                )
        for row in rows.get("usaha", []):
            key = str(row["index1"])
            rosters["businesses"][key] = dict(index=key, label=row.get("nama_usaha") or "Usaha " + key)
        for row in rows.get("meteran", []):
            key = str(row["index_meteran"])
            rosters["meters"][key] = dict(index=key, label="Meteran " + key)
        selections = {}
        for key, wanted in [("businesses", business), ("members", member), ("meters", meter)]:
            if wanted and wanted not in rosters[key]:
                raise HTTPException(422, "ROSTER_KEY_NOT_AVAILABLE")
            selections[key] = wanted or next(iter(rosters[key]), None)
        for row in rows.get("kantor_unit", []):
            if str(row["index_usaha"]) != selections["businesses"]:
                continue
            key = str(row["index_kantor_unit"])
            rosters["offices"][key] = dict(index=key, label=row.get("nama_kantor_unit") or "Kantor " + key)
        if office and office not in rosters["offices"]:
            raise HTTPException(422, "ROSTER_KEY_NOT_AVAILABLE")
        selections["offices"] = office or next(iter(rosters["offices"]), None)

        def selected(sid, roster):
            candidates = rows.get(sid, [])
            if roster:
                column = (
                    "index_meteran"
                    if roster == "meters"
                    else "index_kantor_unit"
                    if roster == "offices"
                    else "index_usaha"
                    if sid == "jaringan_usaha"
                    else "index1"
                )
                candidates = [r for r in candidates if str(r.get(column)) == selections[roster]]
                if roster == "offices":
                    candidates = [
                        r for r in candidates if str(r.get("index_usaha")) == selections["businesses"]
                    ]
            return candidates[0] if len(candidates) == 1 else None

        def eligibility(rule):
            if not rule:
                return None
            sid = rule["source"]
            roster = "members" if sid == "anggota" else "businesses" if sid == "digital_usaha" else None
            row = selected(sid, roster)
            if not row or not present(row.get(rule["field"])):
                return None
            value = row[rule["field"]]
            if "not_applicable_values" in rule:
                return choice_code(value) in rule["not_applicable_values"]
            if "minimum_age" in rule:
                try:
                    age = Decimal(str(value))
                    return 0 <= age < rule["minimum_age"] if age.is_finite() else None
                except InvalidOperation:
                    return None
            return None

        def has_other_version(sid, roster):
            keys, candidates = other_keys.get(sid, ([], []))
            if not roster or not selections.get(roster):
                return bool(candidates)
            column = (
                "index_meteran"
                if roster == "meters"
                else "index_kantor_unit"
                if roster == "offices"
                else "index_usaha"
                if sid == "jaringan_usaha"
                else "index1"
            )
            return any(
                str(row.get(column)) == selections[roster]
                and (roster != "offices" or str(row.get("index_usaha")) == selections["businesses"])
                for row in candidates
            )

        rendered = []
        for section in form["sections"]:
            fields = []
            for schema in section["questions"]:
                result = {
                    k: schema.get(k)
                    for k in [
                        "question_id",
                        "question_text",
                        "mapping_status",
                        "source_object",
                        "source_field",
                        "roster",
                        "converter",
                        "unit",
                        "period",
                        "note",
                    ]
                }
                result.update(value=None, label=None, status="UNVERIFIED_MAPPING", parse_status=None)
                sid = (schema.get("source_object") or "").removeprefix("mart_")
                if schema["mapping_status"] == "NOT_EXPORTED":
                    result["status"] = "NOT_EXPORTED"
                elif schema.get("sensitive") and not can_sensitive:
                    result["status"] = "RESTRICTED"
                elif schema["mapping_status"] == "VERIFIED":
                    row = selected(sid, schema.get("roster"))
                    result["status"] = "BLANK_OR_MISSING"
                    if row:
                        value = row.get(schema["source_field"])
                        label = row.get(schema.get("label_field")) if schema.get("label_field") else None
                        if present(value) or present(label):
                            result.update(
                                value=str(value) if value is not None else None,
                                label=str(label) if label is not None else None,
                                status="ANSWERED",
                            )
                            if schema["converter"] == "decimal":
                                parsed = parse_decimal(
                                    value,
                                    style="auto_strict"
                                    if schema["source_field"] == "total_aset_bln"
                                    else "canonical",
                                )
                                result["parse_status"] = parsed.status
                                result["numeric_value"] = (
                                    format(parsed.value, "f") if parsed.value is not None else None
                                )
                            if schema["source_field"] == "kode_profesi_utama" and value is not None:
                                result["reference_label"] = self.references.professions.get(
                                    str(value).zfill(3)
                                )
                            if schema["source_field"] in ("kbli", "kbli_akhir"):
                                result["reference_label"] = self.references.kbli.get(str(value), {}).get(
                                    "title"
                                )
                        elif eligibility(schema.get("visibility_rule")) is True:
                            result["status"] = "SKIPPED_NOT_APPLICABLE"
                        result["provenance"] = {
                            k: row.get(k) for k in ["__source_sha256", "__batch_id", "__version_normalized"]
                        }
                    elif has_other_version(sid, schema.get("roster")):
                        result["status"] = "UNMATCHED_VERSION"
                    elif eligibility(schema.get("visibility_rule")) is True:
                        result["status"] = "SKIPPED_NOT_APPLICABLE"
                fields.append(result)
            rendered.append(dict(section_id=section["section_id"], title=section["title"], questions=fields))
        return dict(
            form=system,
            assignment=dict(master),
            version=version,
            available_versions=sorted(versions, reverse=True),
            selections=selections,
            rosters={k: list(v.values()) for k, v in rosters.items()},
            sections=rendered,
            modules=[
                dict(
                    source=sid,
                    present=bool(rows[sid]),
                    status="AVAILABLE"
                    if rows[sid]
                    else "UNMATCHED_VERSION"
                    if sid in other_versions
                    else "BLANK_OR_MISSING",
                )
                for sid in source_ids
            ],
            questionnaire_version_status="QUESTIONNAIRE_VERSION_NOT_VERIFIED"
            if system == "ub"
            else "EXACT_NORMALIZED_VERSION",
            read_only=True,
            truncated_rosters=truncated,
            warning="UB: wilayah jawaban dapat memuat fallback master dalam SQL sumber; tidak dipindahkan. PDF menyebut 2025, provenance periode ekspor keuangan belum terverifikasi."
            if system == "ub"
            else "Jawaban hanya dari versi yang dipilih. Ketiadaan jawaban bukan nol atau Tidak.",
        )
