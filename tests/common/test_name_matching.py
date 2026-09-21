import pytest

from pyaml.common.exception import PyAMLException
from pyaml.common.name_matching import is_wildcard, resolve_names

NAMES = ["BPM_C04-01", "BPM_C04-02", "QF1A-C01", "QF1A-C02"]


def test_is_wildcard_triggers_on_star_question_and_bracket():
    assert is_wildcard("BPM*")
    assert is_wildcard("BPM?")
    assert is_wildcard("BPM[01]")
    assert not is_wildcard("BPM_C04-01")
    assert not is_wildcard("re:^BPM")


def test_literal_hit_returns_the_single_name():
    assert resolve_names(NAMES, "QF1A-C01") == ["QF1A-C01"]


def test_literal_miss_raises():
    with pytest.raises(PyAMLException, match="Element UNKNOWN not defined"):
        resolve_names(NAMES, "UNKNOWN")


def test_literal_miss_uses_the_provided_what_label():
    with pytest.raises(PyAMLException, match="Magnet UNKNOWN not defined"):
        resolve_names(NAMES, "UNKNOWN", what="Magnet")


def test_wildcard_hit_and_empty_are_not_errors():
    assert resolve_names(NAMES, "BPM*") == ["BPM_C04-01", "BPM_C04-02"]
    assert resolve_names(NAMES, "MISSING*") == []


def test_wildcard_is_case_sensitive():
    assert resolve_names(NAMES, "bpm*") == []


def test_bracket_only_pattern_is_a_wildcard_not_a_literal():
    assert resolve_names(NAMES, "QF1A-C0[12]") == ["QF1A-C01", "QF1A-C02"]


def test_regex_hit_and_empty_are_not_errors():
    assert resolve_names(NAMES, "re:^BPM_C04-0[12]$") == ["BPM_C04-01", "BPM_C04-02"]
    assert resolve_names(NAMES, "re:^NOTHING$") == []


def test_regex_is_a_fullmatch():
    assert resolve_names(NAMES, "re:BPM_C04") == []


def test_invalid_regex_raises_pyaml_exception_not_re_error():
    with pytest.raises(PyAMLException, match="Invalid regex"):
        resolve_names(NAMES, "re:(")


def test_list_of_patterns_unions_and_deduplicates_in_order():
    result = resolve_names(NAMES, ["QF1A-C01", "BPM*", "QF1A-C01"])
    assert result == ["QF1A-C01", "BPM_C04-01", "BPM_C04-02"]


def test_tuple_of_patterns_is_also_accepted():
    assert resolve_names(NAMES, ("QF1A-C01", "QF1A-C02")) == ["QF1A-C01", "QF1A-C02"]


def test_list_with_one_missing_literal_raises():
    with pytest.raises(PyAMLException, match="Element UNKNOWN not defined"):
        resolve_names(NAMES, ["QF1A-C01", "UNKNOWN"])


def test_list_mixing_literal_wildcard_and_regex():
    result = resolve_names(NAMES, ["QF1A-C01", "BPM*", "re:^QF1A-C02$"])
    assert result == ["QF1A-C01", "BPM_C04-01", "BPM_C04-02", "QF1A-C02"]


def test_overlapping_wildcard_patterns_in_a_list_do_not_duplicate_a_match():
    names = ["BPM_01", "BPM_02", "BPM_03", "BPM_04", "BPM_05"]
    result = resolve_names(names, ["BPM_0[1-3]", "BPM_0[3-5]"])
    assert result == ["BPM_01", "BPM_02", "BPM_03", "BPM_04", "BPM_05"]


def test_lone_exclusion_pattern_means_everything_except():
    assert resolve_names(NAMES, "~QF1A-C01") == ["BPM_C04-01", "BPM_C04-02", "QF1A-C02"]


def test_list_of_only_exclusion_patterns_means_everything_except():
    result = resolve_names(NAMES, ["~QF1A-C01", "~QF1A-C02"])
    assert result == ["BPM_C04-01", "BPM_C04-02"]


def test_exclusion_removes_matches_from_an_inclusion_pattern():
    assert resolve_names(NAMES, ["BPM*", "~BPM_C04-01"]) == ["BPM_C04-02"]


def test_exclusion_order_does_not_matter():
    forward = resolve_names(NAMES, ["BPM*", "~BPM_C04-01"])
    backward = resolve_names(NAMES, ["~BPM_C04-01", "BPM*"])
    assert forward == backward == ["BPM_C04-02"]


def test_exclusion_of_a_wildcard_pattern_removes_all_its_matches():
    result = resolve_names(NAMES, ["QF1A-C01", "QF1A-C02", "BPM_C04-01", "~QF1A-*"])
    assert result == ["BPM_C04-01"]


def test_exclusion_of_a_regex_pattern_removes_all_its_matches():
    result = resolve_names(NAMES, ["BPM*", "~re:^BPM_C04-01$"])
    assert result == ["BPM_C04-02"]


def test_exclusion_of_a_missing_literal_raises():
    with pytest.raises(PyAMLException, match="Element UNKNOWN not defined"):
        resolve_names(NAMES, ["BPM*", "~UNKNOWN"])
