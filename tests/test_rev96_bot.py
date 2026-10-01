import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from togarak_tolov_bot import build_view, month_key, month_title


def test_tolov_view_counts_debt_and_partial():
    text, btns = build_view("Mat <1>", 300000, [(1, "Ali", 300000), (2, "Vali", 100000), (3, "Sardor", None)], "2026-10")
    assert "&lt;1&gt;" in text and "Oktabr 2026" in text
    assert "Qarz: 500 000 so'm" in text and "To'laganlar: 1/3 (+1 qisman)" in text
    assert [b[1] for b in btns] == ["undo", "ok", "ok"]


def test_month_key_wraps_years():
    assert month_key(-10, date(2026, 10, 1)) == "2025-12"
    assert month_key(3, date(2026, 10, 1)) == "2027-01"
    assert month_title("2027-01") == "Yanvar 2027"


def test_dublyaj_keys_and_segments():
    os.environ["GROQ_API_KEYS"] = "a1, b2"
    os.environ["GROQ_API_KEY"] = "b2"
    import dublyaj
    try:
        assert dublyaj._kalitlar("GROQ") == ["a1", "b2"]
        segs = dublyaj._segmentlar_javobdan({"segments": [{"start": 0, "end": 1.234, "text": " Salom "}, {"start": 1, "end": 2, "text": ""}]})
        assert segs == [(0.0, 1.23, "Salom")]
    finally:
        os.environ.pop("GROQ_API_KEYS")
        os.environ.pop("GROQ_API_KEY")
