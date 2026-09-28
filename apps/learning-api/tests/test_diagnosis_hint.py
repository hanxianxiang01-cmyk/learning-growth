"""Diagnosis + Hint 服务测试。"""
from app.services.diagnosis import diagnose
from app.services.hint import decide_hint


def test_diagnose_correct_returns_none():
    assert diagnose(True) is None


def test_diagnose_error_model_mapping():
    d = diagnose(False, error_model="calc")
    assert d.code == "E06"
    assert d.confidence == 0.7


def test_diagnose_fallback_no_hint():
    d = diagnose(False, error_model=None, used_hint_levels=[])
    assert d.code == "E01"


def test_diagnose_strategy_by_high_hint():
    d = diagnose(False, error_model=None, used_hint_levels=[4])
    assert d.code == "E05"


def test_hint_first_error_no_answer_reveal():
    d = decide_hint(attempt_count=1, requested_level=None)
    assert d.answer_revealed is False
    assert d.hint_level == 1


def test_hint_ladder_climbs():
    # 试错次数越多，hint_level 越高，但仍不揭答案
    d3 = decide_hint(attempt_count=3, requested_level=None)
    assert d3.hint_level == 3
    assert d3.answer_revealed is False


def test_hint_cap_at_max():
    d = decide_hint(attempt_count=9, requested_level=None)
    assert d.hint_level == 4
    assert d.answer_revealed is False