import sqlite3

from se2026.common import sha256
from se2026.web.business_directory import coordinates

from .synthetic import V1, V2


def test_priority_sort_is_global_before_pagination(portal):
    app, client, _ = portal
    app.state.directory.ensure()
    with app.state.app_db.connection() as con:
        for aid, code, title in [
            ("DTD-0001", "00", "AAA"),
            ("DTD-0002", "9", "AAA"),
            ("DTD-0003", "3", "AAA"),
            ("DTD-0004", "4", "AAA"),
            ("DTD-0005", "2", "AAA"),
            ("DTD-0006", "1", "ZZZ"),
            ("DTD-0007", "1", "aaa"),
        ]:
            con.execute(
                "UPDATE directory_rows SET status=?,title=? WHERE scope='businesses' AND source='dtd' AND assignment_id=?",
                (code, title, aid),
            )
    body = {"source": "dtd", "sort": "business_priority", "page_size": 100}
    result = client.post("/api/v1/directories/businesses/search", json=body).json()
    ranks = {"1": 0, "2": 1, "4": 2, "3": 3, "9": 4, "00": 5}
    scores = app.state.directory.completeness_scores("admin")
    keys = [
        (ranks.get(row["status"], 6), -scores[row["record_key"]], row["title"].lower())
        for row in result["rows"]
    ]
    assert keys == sorted(keys)
    first = client.post(
        "/api/v1/directories/businesses/search", json={**body, "page_size": 2, "page": 1}
    ).json()
    second = client.post(
        "/api/v1/directories/businesses/search", json={**body, "page_size": 2, "page": 2}
    ).json()
    assert [row["record_key"] for row in first["rows"] + second["rows"]] == [
        row["record_key"] for row in result["rows"][:4]
    ]


def test_business_people_and_tagging_use_exact_version_roster_and_role(portal, analyst):
    app, client, settings = portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute(
            "UPDATE mart_usaha SET nama_pengusaha_pj='SYNTHETIC PJ',geotag_latitude='2.125',geotag_longitude='117.25' WHERE assignment_id='DTD-0001' AND __version_normalized=? AND index1='001'",
            (V1,),
        )
        con.execute(
            "UPDATE mart_keluarga SET nama_kk='SYNTHETIC KK' WHERE assignment_id='DTD-0001' AND __version_normalized=?",
            (V1,),
        )
        con.execute("UPDATE mart_keluarga SET __version_normalized=? WHERE assignment_id='DTD-0002'", (V2,))
        con.execute(
            "UPDATE mart_usaha SET nama_pengusaha_pj='SYNTHETIC FALLBACK' WHERE assignment_id='DTD-0002'"
        )
        con.execute(
            "UPDATE mart_ub_a SET nama_penanggung_jawab='SYNTHETIC UB PJ',link_google_maps='https://www.google.com/maps/search/?api=1&query=2.125,117.25' WHERE assignment_id='UB-0001'"
        )
    before = sha256(settings.census_db)
    body = {"source": "dtd", "q": "DTD-0001", "page_size": 100}
    result = client.post("/api/v1/directories/businesses/search", json=body).json()
    exact = next(row for row in result["rows"] if row["version"] == V1 and row["index1"] == "001")
    assert exact["family_head"] == "SYNTHETIC KK" and exact["person_in_charge"] == "SYNTHETIC PJ"
    assert exact["map_coordinates"] == {"latitude": "2.125", "longitude": "117.25"}
    others = [row for row in result["rows"] if row["version"] != V1 or row["index1"] != "001"]
    assert all(row["map_coordinates"] is None for row in others)
    fallback = client.post(
        "/api/v1/directories/businesses/search", json={"source": "dtd", "q": "DTD-0002"}
    ).json()["rows"][0]
    assert fallback["family_head"] is None and fallback["person_in_charge"] == "SYNTHETIC FALLBACK"
    restricted = analyst.post("/api/v1/directories/businesses/search", json=body).json()
    assert all(
        row["map_coordinates"] is None and row["map_status"] == "RESTRICTED" for row in restricted["rows"]
    )
    assert "117.25" not in str(restricted)
    ub = client.post("/api/v1/directories/businesses/search", json={"source": "ub", "q": "UB-0001"}).json()[
        "rows"
    ][0]
    assert ub["person_in_charge"] == "SYNTHETIC UB PJ" and ub["family_head"] is None
    assert ub["map_coordinates"] == {"latitude": "2.125", "longitude": "117.25"}
    assert len({row["record_key"] for row in result["rows"]}) == len(result["rows"])
    assert sha256(settings.census_db) == before


def test_coordinate_validation_never_invents_zero_or_accepts_invalid_values():
    for lat, lon in [(None, None), ("NaN", "117"), ("91", "117"), ("2", "181"), ("0", "0"), ("2,1", "117")]:
        assert coordinates(lat, lon) is None
    assert coordinates("0", "117") == {"latitude": "0", "longitude": "117"}


def test_complete_business_precedes_alphabetical_name_within_status(portal):
    app, client, settings = portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute(
            "UPDATE mart_usaha SET nama_pengusaha_pj='SYNTHETIC PJ',geotag_latitude='2.125',geotag_longitude='117.25' WHERE assignment_id IN ('DTD-0001','DTD-0002')"
        )
    app.state.directory.ensure()
    with app.state.app_db.connection() as con:
        con.execute(
            "UPDATE directory_rows SET title='ZZZ COMPLETE',status='1',kbli='01111',kategori='A' WHERE scope='businesses' AND source='dtd' AND assignment_id='DTD-0001'"
        )
        con.execute(
            "UPDATE directory_rows SET title='BBB COMPLETE',status='1',kbli='01111',kategori='A' WHERE scope='businesses' AND source='dtd' AND assignment_id='DTD-0002'"
        )
        con.execute(
            "UPDATE directory_rows SET title='AAA INCOMPLETE',status='1',kbli=NULL,kategori=NULL WHERE scope='businesses' AND source='dtd' AND assignment_id='DTD-0003'"
        )
    result = client.post(
        "/api/v1/directories/businesses/search",
        json={"source": "dtd", "sort": "business_priority", "page_size": 100},
    ).json()
    titles = [row["title"] for row in result["rows"]]
    assert titles.index("BBB COMPLETE") < titles.index("ZZZ COMPLETE") < titles.index("AAA INCOMPLETE")
    first = client.post(
        "/api/v1/directories/businesses/search",
        json={"source": "dtd", "sort": "business_priority", "page_size": 1},
    ).json()
    assert first["rows"][0]["title"] == "BBB COMPLETE"
