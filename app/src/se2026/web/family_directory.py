"""Enrich visible family/member rows using the exact family-version key."""

from collections import defaultdict

from .business_directory import coordinates
from .database import census_connection


def enrich_family_records(settings, rows, role, scope):
    if not rows:
        return rows
    ids = sorted({row["assignment_id"] for row in rows})
    condition = " WHERE assignment_id IN (" + ",".join("?" for _ in ids) + ")" if len(ids) <= 1000 else ""
    sensitive = role == "admin" and scope == "families"
    fields = "assignment_id,__version_normalized,nama_kk"
    if sensitive:
        fields += ",geotag_latitude,geotag_longitude"
    families = defaultdict(list)
    with census_connection(settings) as con:
        for item in con.execute("SELECT " + fields + " FROM mart_keluarga" + condition, ids if condition else []):
            families[(item["assignment_id"], item["__version_normalized"])].append(dict(item))
    for row in rows:
        matches = families[(row["assignment_id"], row["version"])]
        row["family_head"] = matches[0]["nama_kk"] or None if len(matches) == 1 else None
        if scope != "families":
            continue
        row.update(map_coordinates=None, map_status="RESTRICTED", map_provenance="FAMILY_QUESTIONNAIRE_TAG")
        if not sensitive:
            continue
        row["map_status"] = "SOURCE_CONFLICT" if len(matches) > 1 else "UNAVAILABLE"
        if len(matches) == 1:
            row["map_coordinates"] = coordinates(matches[0]["geotag_latitude"], matches[0]["geotag_longitude"])
            if row["map_coordinates"]:
                row["map_status"] = "AVAILABLE"
    return rows
