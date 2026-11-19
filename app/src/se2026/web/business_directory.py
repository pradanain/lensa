"""Page-scoped business enrichment with exact source keys and no row multiplication."""

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urlsplit

from .database import census_connection
from .detail_access import full_address


def coordinates(latitude, longitude):
    try:
        lat, lon = Decimal(str(latitude)), Decimal(str(longitude))
        if not lat.is_finite() or not lon.is_finite():
            return None
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            return None
        return dict(latitude=str(lat), longitude=str(lon))
    except (InvalidOperation, ValueError):
        return None


def map_link_coordinates(value):
    """Read a coordinate pair from an exported Google Maps link, without network access."""
    try:
        link = urlsplit(str(value or ""))
    except ValueError:
        return None
    if link.scheme == "https" and link.hostname == "www.google.com" and link.path == "/maps/search/":
        query = parse_qs(link.query).get("query", [])
        if len(query) == 1 and len(query[0].split(",")) == 2:
            return coordinates(*query[0].split(","))
    return None


def enrich_businesses(settings, rows, role):
    if not rows:
        return rows
    ids = sorted({row["assignment_id"] for row in rows})
    placeholders = ",".join("?" for _ in ids)
    # Ranking reads the whole business directory once; page enrichment stays bounded.
    condition = " WHERE assignment_id IN (" + placeholders + ")" if len(ids) <= 1000 else ""
    bindings = ids if condition else []
    businesses, families, ub, legal = (defaultdict(list) for _ in range(4))
    sensitive = role == "admin"
    with census_connection(settings) as con:
        dtd_fields = "assignment_id,__version_normalized,index1,nama_pengusaha_pj,alamat_usaha,geotag_latitude,geotag_longitude"
        for item in con.execute("SELECT " + dtd_fields + " FROM mart_usaha" + condition, bindings):
            businesses[(item["assignment_id"], item["__version_normalized"], item["index1"])].append(
                dict(item)
            )
        for item in con.execute(
            "SELECT assignment_id,__version_normalized,nama_kk FROM mart_keluarga" + condition,
            bindings,
        ):
            families[(item["assignment_id"], item["__version_normalized"])].append(item["nama_kk"])
        legal_fields = "assignment_id,__version_normalized,index1,nama_pengusaha_pj,nomor_telepon,nomor_hp_whatsapp"
        if sensitive:
            legal_fields += ",nik_pengusaha_pj"
        for item in con.execute("SELECT " + legal_fields + " FROM mart_legalitas_usaha" + condition, bindings):
            legal[(item["assignment_id"], item["__version_normalized"], item["index1"])].append(dict(item))
        ub_fields = "assignment_id,nama_penanggung_jawab,alamat_usaha,nomor_hp_usaha,link_google_maps"
        if sensitive:
            ub_fields += ",nik_penanggung_jawab"
        for item in con.execute(
            "SELECT " + ub_fields + " FROM mart_ub_a" + condition,
            bindings,
        ):
            ub[item["assignment_id"]].append(dict(item))
    for row in rows:
        row.update(person_in_charge=None, person_in_charge_nik=None, family_head=None,
                   business_address=None, business_phone=None, business_mobile=None, map_coordinates=None)
        row["map_provenance"] = "QUESTIONNAIRE_ROOT_TAG" if row["source"] == "dtd" else "UB_EXPORTED_MAP_LINK"
        if row["source"] == "dtd":
            matches = businesses[(row["assignment_id"], row["version"], row["index1"])]
            if len(matches) == 1:
                item = matches[0]
                row["person_in_charge"] = item["nama_pengusaha_pj"] or None
                row["business_address"] = item["alamat_usaha"] or None
                row["map_coordinates"] = coordinates(item["geotag_latitude"], item["geotag_longitude"])
            identities = legal[(row["assignment_id"], row["version"], row["index1"])]
            if len(matches) == 1 and len(identities) == 1:
                identity = identities[0]
                row["person_in_charge"] = identity["nama_pengusaha_pj"] or row["person_in_charge"]
                row["person_in_charge_nik"] = identity.get("nik_pengusaha_pj") if sensitive else None
                row["business_phone"] = identity["nomor_telepon"] or None
                row["business_mobile"] = identity["nomor_hp_whatsapp"] or None
            heads = families[(row["assignment_id"], row["version"])]
            if len(heads) == 1:
                row["family_head"] = heads[0] or None
        elif len(ub[row["assignment_id"]]) == 1:
            item = ub[row["assignment_id"]][0]
            row["person_in_charge"] = item["nama_penanggung_jawab"] or None
            row["person_in_charge_nik"] = item.get("nik_penanggung_jawab") if sensitive else None
            row["business_address"] = item["alamat_usaha"] or None
            row["business_mobile"] = item["nomor_hp_usaha"] or None
            # Decode the already-exported coordinate pair, without resolving a URL.
            row["map_coordinates"] = map_link_coordinates(item["link_google_maps"])
        row["full_address"] = full_address(row["business_address"], row.get("desa_label"), row.get("kecamatan_label"))
        row["map_status"] = (
            "AVAILABLE" if row["map_coordinates"] else "UNAVAILABLE"
        )
    return rows
