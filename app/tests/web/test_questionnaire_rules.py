import sqlite3

import pytest
from se2026.web.questionnaire_rules import UNKNOWN, apply_display_rules, compile_condition, evaluate

from .test_api import fields


@pytest.mark.parametrize(
    "source,expected",
    [
        ("let a=getValue('age'); Number(a) >= 5;", True),
        ("['1','2'].includes(getValue('kind')?.[0]?.value)", True),
        ("getValue('missing') && false", False),
        ("getValue('missing') || true", True),
        ("!getValue('missing')", UNKNOWN),
        ("(function(){ let a=getValue('age'); return Number(a) < 5; })()", False),
        ("let a=getValue('age') ?? 0;\nlet year='2026'\nNumber(a) == year;", False),
    ],
)
def test_safe_expression_subset_has_conservative_unknowns(source, expected):
    facts = {"age": "12", "kind": "1"}
    assert evaluate(compile_condition(source), lambda key: facts.get(key, UNKNOWN)) is expected


def test_unsupported_js_and_missing_drivers_are_never_executed_or_guessed():
    for source in [
        "__import__('os').system('anything')",
        "fetch('https://example.invalid')",
        "if(true){return false}",
        "getConfig('user')",
        "getValue('x') === 1",
    ]:
        assert evaluate(compile_condition(source), lambda _: UNKNOWN) is UNKNOWN
    assert evaluate(compile_condition("getValue('missing') == 0"), lambda _: UNKNOWN) is UNKNOWN


@pytest.mark.parametrize(
    "year,annual,monthly", [("2007", "UNKNOWN", "HIDDEN"), ("2026", "HIDDEN", "UNKNOWN")]
)
def test_annual_and_monthly_branches_follow_template_year_without_deleting_answers(
    portal, year, annual, monthly
):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_program_usaha SET tahun_mulai_operasi=? WHERE assignment_id='DTD-0001'", (year,)
        )
        con.execute(
            "UPDATE mart_ekonomi_bulanan SET total_pendapatan_bln='12345' WHERE assignment_id='DTD-0001'"
        )
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    assert answer["blokl.gaji"]["display_state"] == annual
    assert answer["blokl.total_pendapatan_bln"]["display_state"] == monthly
    assert answer["blokl.total_pendapatan_bln"]["value"] == "12345"


def test_nib_cooperative_and_internet_branches_hide_only_when_proven_false(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_legalitas_usaha SET punya_nib='2',badan_usaha='13' WHERE assignment_id='DTD-0001'"
        )
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    assert answer["blokl.nib"]["display_state"] == "HIDDEN"
    assert answer["blokl.tidak_nib"]["display_state"] != "HIDDEN"
    assert answer["blokl.jenis_koperasi"]["display_state"] == "HIDDEN"
    assert answer["blokl.internet_pesanan"]["display_state"] == "HIDDEN"


def test_missing_or_unrecognized_choice_driver_keeps_uncertainty(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_legalitas_usaha SET punya_nib=NULL,badan_usaha='99' WHERE assignment_id='DTD-0001'"
        )
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    assert answer["blokl.nib"]["display_state"] == "UNKNOWN"
    assert answer["blokl.tidak_nib"]["display_state"] == "UNKNOWN"
    assert answer["blokl.jenis_koperasi"]["display_state"] == "UNKNOWN"


def test_consolidated_pj_and_final_kbli_remain_available_on_family_assignments(portal):
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    for key in ["pengusaha", "jk", "umur", "nik_pengusaha", "kbli"]:
        assert answer["blokl." + key]["display_state"] != "HIDDEN"


def test_age_and_school_participation_conditions_use_selected_member(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute("UPDATE mart_anggota SET umur='4' WHERE assignment_id='DTD-0001' AND index1='001'")
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001", params={"member": "001"}).json())
    assert answer["b_ak_lanjutan.sekolah"]["display_state"] == "HIDDEN"
    assert answer["b_ak_lanjutan.profesi"]["display_state"] == "HIDDEN"


def test_house_ownership_controls_rent_items_and_supports_source_labels(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_perumahan SET status_kepemilikan='2. Kontrak/sewa' WHERE assignment_id='DTD-0001'"
        )
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    assert answer["b_perumahan.sewa_sendiri"]["display_state"] == "HIDDEN"
    assert answer["b_perumahan.sewa_dinas"]["display_state"] == "HIDDEN"
    assert answer["b_perumahan.sewa_kontrak"]["display_state"] != "HIDDEN"


def test_restricted_driver_cannot_be_reconstructed_from_computed_variable():
    form = {
        "sections": [
            {
                "section_id": "b5",
                "questions": [
                    {"question_id": "driver", "template_key": "private"},
                    {
                        "question_id": "child",
                        "display_rules": [compile_condition("getValue('private') == '1'")],
                    },
                ],
            }
        ],
        "display_variables": {"private": {"literal": "2"}},
    }
    rendered = [
        {
            "section_id": "b5",
            "questions": [
                {"question_id": "driver", "status": "RESTRICTED", "value": None},
                {"question_id": "child", "status": "BLANK_OR_MISSING"},
            ],
        }
    ]
    apply_display_rules(form, rendered)
    assert rendered[0]["questions"][1]["display_state"] == "UNKNOWN"


def test_conflicting_control_projections_do_not_choose_a_branch():
    form = {
        "sections": [
            {
                "section_id": "b5",
                "questions": [{"question_id": key, "template_key": "driver"} for key in ["a", "b"]]
                + [
                    {
                        "question_id": "child",
                        "display_rules": [compile_condition("getValue('driver') == '1'")],
                    }
                ],
            }
        ]
    }
    rendered = [
        {
            "section_id": "b5",
            "questions": [
                {"question_id": "a", "status": "ANSWERED", "value": "1"},
                {"question_id": "b", "status": "ANSWERED", "value": "2"},
                {"question_id": "child", "status": "BLANK_OR_MISSING"},
            ],
        }
    ]
    apply_display_rules(form, rendered)
    assert rendered[0]["questions"][2]["display_state"] == "UNKNOWN"


def test_negative_age_is_unknown_and_member_selection_does_not_borrow_another_row(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute("UPDATE mart_anggota SET umur='4' WHERE assignment_id='DTD-0001' AND index1='001'")
        con.execute("UPDATE mart_anggota SET umur='-1' WHERE assignment_id='DTD-0001' AND index1='002'")
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001", params={"member": "002"}).json())
    assert answer["b_ak_lanjutan.sekolah"]["display_state"] != "HIDDEN"
