from src.parser import parse_results
from src.quality import annotate, quality_messages, truncated


def test_disagreement_flagged_not_changed():
    a = parse_results("MCV 4.2 fL 83 - 101")
    b = parse_results("MCV 84.2 fL 83 - 101")
    annotate(a, b)
    assert a[0].value == 4.2 and a[0].alt == 84.2 and a[0].review
    assert "disagree" in a[0].note


def test_agreement_not_flagged():
    a = parse_results("Hemoglobin 12.7 g/dL 12 - 15")
    annotate(a, parse_results("Hemoglobin 12.7 g/dL 12 - 15"))
    assert not a[0].review


def test_truncated_names():
    assert truncated("rystals") and not truncated("Crystals")


def test_few_rows_message():
    assert any("Retake" in m for m in quality_messages([], []))