"""Enrich visible family/member rows using the exact family-version key."""

from collections import defaultdict
import re

from .business_directory import coordinates
from .database import census_connection


def enrich_family_records(settings, rows, role, scope):
    if not rows:
        return rows
    ids = sorted({row["assignment_id"] for row in rows})
    condition = " WHERE assignment_id IN (" + ",".join("?" for _ in ids) + ")" if len(ids) <= 1000 else ""
    sensitive = role == "admin" and scope == "families"
    fields = "assignment_id,__version_normalized,nama_kk"
    if scope == "families":
        fields += ",nomor_bangunan,jumlah_anggota_hasil_pendataan,jumlah_usaha_ditemukan"
    if sensitive:
        fields += ",alamat_keluarga,geotag_latitude,geotag_longitude"
    families = defaultdict(list)
    members = defaultdict(list)
    with census_connection(settings) as con:
        if scope == "members":
            columns = "assignment_id,__version_normalized,index1,nomor_urut_anggota,umur,kode_hubungan,hubungan_kepala_keluarga,kode_jenis_kelamin,jenis_kelamin,kode_memiliki_usaha,memiliki_usaha"
            if role == "admin":
                columns += ",nik_anggota"
            for item in con.execute("SELECT " + columns + " FROM mart_anggota" + condition, ids if condition else []):
                members[(item["assignment_id"], item["__version_normalized"], item["index1"])].append(dict(item))
        for item in con.execute("SELECT " + fields + " FROM mart_keluarga" + condition, ids if condition else []):
            families[(item["assignment_id"], item["__version_normalized"])].append(dict(item))
    for row in rows:
        matches = families[(row["assignment_id"], row["version"])]
        row["family_head"] = matches[0]["nama_kk"] or None if len(matches) == 1 else None
        if scope != "families":
            values = members[(row["assignment_id"], row["version"], row["index1"])]
            item = values[0] if len(values) == 1 else {}
            row["member_nik"] = item.get("nik_anggota") if role == "admin" else None
            row["member_number"] = item.get("nomor_urut_anggota")
            row["member_age"] = item.get("umur")
            for target, code, label, choices in [
                ("member_relationship", "kode_hubungan", "hubungan_kepala_keluarga", {"1":"Kepala Keluarga","2":"Istri/Suami","3":"Anak","4":"Menantu","5":"Cucu","6":"Orang Tua","7":"Mertua","8":"Famili","9":"Lainnya"}),
                ("member_gender", "kode_jenis_kelamin", "jenis_kelamin", {"1":"Laki-laki","2":"Perempuan"}),
                ("member_business", "kode_memiliki_usaha", "memiliki_usaha", {"1":"Ya","2":"Tidak"}),
            ]:
                source = str(item.get(label) or "").strip()
                row[target] = re.sub(r"^\d+\s*[.)\-:]\s*", "", source) if source and source != str(item.get(code)) else choices.get(str(item.get(code)))
            continue
        for name, column in [("building_number", "nomor_bangunan"), ("member_count", "jumlah_anggota_hasil_pendataan"), ("business_count", "jumlah_usaha_ditemukan")]:
            row[name] = matches[0][column] if len(matches) == 1 else None
        row["family_address"] = matches[0]["alamat_keluarga"] if sensitive and len(matches) == 1 else None
        row.update(map_coordinates=None, map_status="RESTRICTED", map_provenance="FAMILY_QUESTIONNAIRE_TAG")
        if not sensitive:
            continue
        row["map_status"] = "SOURCE_CONFLICT" if len(matches) > 1 else "UNAVAILABLE"
        if len(matches) == 1:
            row["map_coordinates"] = coordinates(matches[0]["geotag_latitude"], matches[0]["geotag_longitude"])
            if row["map_coordinates"]:
                row["map_status"] = "AVAILABLE"
    return rows
