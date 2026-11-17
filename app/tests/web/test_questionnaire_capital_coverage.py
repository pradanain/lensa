import sqlite3

from se2026.common import sha256

from .test_api import fields


def test_annual_capital_is_unexported_and_does_not_borrow_founding_capital(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_ekonomi_bulanan SET modal_pribadi_persen='100' WHERE assignment_id='DTD-0001'"
        )
    before = sha256(portal[2].census_db)
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    assert answer["blokl.pribadi_didirikan"]["status"] == "ANSWERED"
    assert answer["blokl.pribadi_didirikan"]["value"] == "100"
    for key in ["pribadi", "non_profit", "publik", "non_publik", "pemerintah", "asing", "info_total"]:
        field = answer["blokl." + key]
        assert field["status"] == "NOT_EXPORTED"
        assert field["value"] is None
        assert field["availability_group"] == "annual_capital"
        assert "isian berbeda" in field["availability_note"]
    assert sha256(portal[2].census_db) == before
