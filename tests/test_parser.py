from src.parser import parse_results, parse_qualitative


def one(line):
    r = parse_results(line)
    assert len(r) == 1, f"not parsed: {line}"
    return r[0]


def test_plain_range():
    r = one("Hemoglobin » 12.7 gm% 12-16 ie")
    assert (r.name, r.value, r.unit, r.low, r.high) == ("Hemoglobin", 12.7, "gm%", 12, 16)
    assert not r.review


def test_upper_and_lower_limits():
    assert one("Cholesterol Total 150 <200 mg/dL").high == 200
    r = one("HDL Cholesterol 44 >40 mg/dL")
    assert r.low == 40 and r.high is None


def test_lost_decimal_is_flagged_not_fixed():
    r = one("R.B.C. count : 445 mil./cmm 3.8-4.8")
    assert r.value == 445 and r.review and r.suggested == 4.45
    r = one("MPV : 92 fL 7.4-11.0")
    assert r.review and r.suggested == 9.2


def test_printed_flag_mismatch():
    r = one("HDL CHOLESTEROL 274 L 30-95 mg %")
    assert r.review and r.suggested == 27.4 and r.printed_flag == "L"


def test_printed_flag_consistent():
    r = one("TRIGLYCERIDES 154.6 oH 0-150 mg %")
    assert r.printed_flag == "H" and not r.review


def test_mangled_value():
    assert one("MCHC 1 2 em/dl 32 - 36").review


def test_unit_fixes():
    assert one("MCV : 87.4 {L 76-96").unit == "fL"
    assert one("Platelet Count : 308000 /omm 150000 - 400000").unit == "/cmm"


def test_ph_with_ocr_damaged_range():
    r = one("Reaction (pH) : 6.0 §.0- 8.0")
    assert r.value == 6.0 and (r.low, r.high) == (5.0, 8.0)


def test_qualitative():
    text = ("Colour Pale Yellow Yellow - Straw\n"
            "Glucose : Absent Absent\n"
            "Red Blood Cells : Absent Nil\n"
            "Proteins : Present Absent")
    st = {q.name: q.status for q in parse_qualitative(text)}
    assert st == {"Colour": "Normal", "Glucose": "Normal",
                  "Red Blood Cells": "Normal", "Proteins": "Abnormal"}


def test_dates_and_headers_ignored():
    assert parse_results("Date: 12-03-2025\nPatient Age 34 Sex F") == []
    
def test_thousands_comma():
    assert one("TOTAL LEUCOCYTE COUNT (TLC) 7,800 /cumm 4000 - 11000").value == 7800
    assert one("Platelet Count 1,50,000 /cumm 150000 - 410000").value == 150000


def test_flag_words_are_not_units():
    r = one("Hemoglobin (Hb) 12.5 Low 13 - 17 g/dL")
    assert r.printed_flag == "L" and r.unit == "g/dL" and not r.review


def test_watermark_removed():
    r = one("Neutrophils 60 % Drlogy.com50 - 62")
    assert r.unit == "%" and (r.low, r.high) == (50, 62)


def test_glued_unit_and_range():
    r = one("Platelet Count 150000 Borderline150000 - 410000 /cumm")
    assert r.unit == "/cumm" and r.low == 150000
    assert one("Absolute Neutrophil Count 2350 Cells/cumm2000 - 7000").low == 2000


def test_damaged_ranges_flagged():
    assert one("Neutrophils 30 % 40 - 30").review
    assert one("RBC COUNT 4.1 Millions/emm3.8 - 48").review


def test_value_far_outside_range():
    assert one("MCV $ 4.2 fl 83 - 101").review


def test_name_junk_removed():
    assert one("Monocytes sy 8 % 2 - 10").name == "Monocytes"
    assert one("RDW $ 13.5 % 11.6 - 14").name == "RDW"


def test_interpretation_table_ignored():
    assert parse_results("Optimal <200\nHigh >240 200 - 499\nVery High - >500") == []


def test_hpf_rows():
    text = ("Epithelial Cells : 1-2/hpf /hpf 0 - 2/hpf\n"
            "Leucocytes ; 1-3/hpf Ihpf 0 - 5/hpf\n"
            "Pus Cells 8-10/hpf 0 - 5/hpf")
    st = [q.status for q in parse_qualitative(text)]
    assert st == ["Normal", "Normal", "Abnormal"]

def test_range_lost_decimal_both_sides():
    r = one("HAEMOGLOBIN 14.4 g/dl 115 - 165")
    assert r.review and "11.5 - 16.5" in r.note


def test_exponent_unit_not_taken_as_value():
    r = one("PLT 201 10°/1 100 - 400")
    assert r.value == 201 and r.name == "PLT" and r.unit == "10^n"


def test_interpretation_row_with_numbers_ignored():
    assert parse_results("Above Optimal 100 - 129 130 - 159") == []


def test_unknown_unit_flagged():
    assert one("Hemoglobin 12.7 zzq 12 - 16").review


def test_differential_check():
    from src.parser import parse_results as pr
    from src.checks import differential_check
    ok = pr("Neutrophils 60 % 40 - 75\nLymphocytes 30 % 20 - 40\n"
            "Eosinophils 3 % 1 - 6\nMonocytes 6 % 2 - 10\nBasophils 1 % 0 - 1")
    assert differential_check(ok) is None
    bad = pr("Neutrophils 30 % 40 - 75\nLymphocytes 30 % 20 - 40\n"
             "Eosinophils 3 % 1 - 6\nMonocytes 6 % 2 - 10\nBasophils 1 % 0 - 1")
    assert "sums to 70" in differential_check(bad)