# tests/test_yellow_pages.py
#
# Self-contained tests for fully dynamic YellowPages (no register).
# Comments are in English.

import re

import pytest

from pyaml.yellow_pages import (
    YellowPages,
    YellowPagesCategory,
    YellowPagesError,
    YellowPagesQueryError,
)

# ---------------------------
# Minimal test doubles
# ---------------------------


class _Holder:
    """Minimal ElementHolder double with discovery + resolution."""

    def __init__(self, arrays=None, tools=None, diagnostics=None):
        self._arrays = dict(arrays or {})
        self._tools = dict(tools or {})
        self._diagnostics = dict(diagnostics or {})

    # Discovery
    def list_arrays(self) -> set[str]:
        return set(self._arrays.keys())

    def list_tools(self) -> set[str]:
        return set(self._tools.keys())

    def list_diagnostics(self) -> set[str]:
        return set(self._diagnostics.keys())

    # Resolution
    def get_array(self, name: str):
        if name not in self._arrays:
            raise KeyError(name)
        return self._arrays[name]

    def get_tool(self, name: str):
        if name not in self._tools:
            raise KeyError(name)
        return self._tools[name]

    def get_diagnostic(self, name: str):
        if name not in self._diagnostics:
            raise KeyError(name)
        return self._diagnostics[name]


class _Accelerator:
    """Minimal Accelerator double."""

    def __init__(self, controls: dict[str, _Holder], simulators: dict[str, _Holder]):
        self._controls = dict(controls)
        self._simulators = dict(simulators)
        self._modes = {**self._controls, **self._simulators}

    def controls(self) -> dict[str, _Holder]:
        return dict(self._controls)

    def simulators(self) -> dict[str, _Holder]:
        return dict(self._simulators)

    def modes(self) -> dict[str, _Holder]:
        return dict(self._modes)


# ---------------------------
# Fixtures
# ---------------------------


@pytest.fixture()
def accelerator():
    # Controls
    live = _Holder(
        arrays={
            "BPM": ["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"],
            "HCORR": ["CH_C01-01", "CH_C01-02"],
        },
        tools={"DEFAULT_ORBIT_CORRECTION": object()},
        diagnostics={"DEFAULT_BETATRON_TUNE_MONITOR": object()},
    )
    tango = _Holder(
        arrays={
            "BPM": ["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"],  # same as live
            # HCORR missing in tango
        },
        tools={},  # tool missing
        diagnostics={},  # diag missing
    )

    # Simulators
    design = _Holder(
        arrays={
            "BPM": ["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"],
            "HCORR": ["CH_C01-01"],  # different size than live
        },
        tools={"DEFAULT_ORBIT_CORRECTION": object()},
        diagnostics={},  # missing
    )

    return _Accelerator(
        controls={"live": live, "tango": tango}, simulators={"design": design}
    )


@pytest.fixture()
def yp(accelerator):
    return YellowPages(accelerator)


# ---------------------------
# Discovery API
# ---------------------------


def test_has_and_keys_discovery(yp):
    assert yp.has("BPM")
    assert yp.has("HCORR")
    assert yp.has("DEFAULT_ORBIT_CORRECTION")
    assert yp.has("DEFAULT_BETATRON_TUNE_MONITOR")
    assert not yp.has("DOES_NOT_EXIST")

    assert yp.keys(YellowPagesCategory.ARRAYS) == ["BPM", "HCORR"]
    assert yp.keys(YellowPagesCategory.TOOLS) == ["DEFAULT_ORBIT_CORRECTION"]
    assert yp.keys(YellowPagesCategory.DIAGNOSTICS) == ["DEFAULT_BETATRON_TUNE_MONITOR"]


def test_categories_returns_only_present_categories(yp):
    # All three categories are present in our fixture
    assert yp.categories() == ["Arrays", "Tools", "Diagnostics"]


def test_dir_includes_attribute_friendly_keys_only(yp):
    d = dir(yp)
    # Attribute-friendly discovered keys should be included
    assert "BPM" in d
    assert "HCORR" in d
    assert "DEFAULT_ORBIT_CORRECTION" in d

    # Non-existent keys not present
    assert "DOES_NOT_EXIST" not in d


def test_getattr_returns_multimode_resolution_dict(yp):
    bpm = yp.BPM
    assert isinstance(bpm, dict)
    assert set(bpm.keys()) == {"live", "tango", "design"}


# ---------------------------
# Resolution
# ---------------------------


def test_availability(yp):
    assert yp.availability("BPM") == {"live", "tango", "design"}
    assert yp.availability("HCORR") == {"live", "design"}


def test_unknown_key_errors(yp):
    with pytest.raises(YellowPagesQueryError, match=r"Unknown YellowPages key"):
        _ = yp["DOES_NOT_EXIST"]


# ---------------------------
# __repr__ formatting (controls/simulators + sizes + modes)
# ---------------------------


def test_repr_has_controls_and_simulators_headers(yp):
    s = repr(yp)
    assert "Controls:" in s
    assert "Simulators:" in s

    assert re.search(r"^\s+live$", s, re.M) is not None
    assert re.search(r"^\s+tango$", s, re.M) is not None
    assert re.search(r"^\s+design$", s, re.M) is not None


def test_repr_array_size_compaction_when_identical_everywhere(yp):
    # BPM has same size in all modes => should show "size=3"
    s = repr(yp)
    bpm_line = next(line for line in s.splitlines() if line.strip().startswith("BPM"))
    assert "size=3" in bpm_line
    assert "size={" not in bpm_line


def test_repr_array_size_dict_when_different_or_not_everywhere(yp):
    # HCORR differs in size between live (2) and design (1) and missing in tango
    s = repr(yp)
    hcorr_line = next(
        line for line in s.splitlines() if line.strip().startswith("HCORR")
    )
    assert "size={" in hcorr_line
    assert "live:2" in hcorr_line
    assert "design:1" in hcorr_line
    assert "modes=" in hcorr_line
    assert "missing=" in hcorr_line


def test_repr_tools_show_modes_missing(yp):
    s = repr(yp)
    tool_line = next(
        line for line in s.splitlines() if "DEFAULT_ORBIT_CORRECTION" in line
    )
    assert "modes=" in tool_line
    assert "missing=" in tool_line


# ---------------------------
# Query language (__getitem__)
# ---------------------------


def test_query_single_key_returns_union_of_ids_across_modes(yp):
    out = yp["BPM"]
    assert out == ["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"]


def test_query_union_operator(yp):
    out = yp["HCORR|BPM"]
    assert "CH_C01-01" in out
    assert "CH_C01-02" in out
    assert "BPM_C01-01" in out


def test_query_intersection_operator(yp):
    assert yp["BPM&HCORR"] == []


def test_query_difference_operator(yp):
    out = yp["BPM - re{BPM_C01-01}"]
    assert out == ["BPM_C01-02", "BPM_C02-01"]


def test_query_parentheses_precedence(yp):
    out = yp["(BPM|HCORR) - re:CH_.*"]
    assert out == ["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"]


def test_query_regex_alone_filters_all_known_ids(yp):
    out = yp["re:^BPM_"]
    assert out == ["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"]


def test_query_tokenize_errors_raise(yp):
    with pytest.raises(YellowPagesQueryError, match=r"Empty YellowPages query"):
        _ = yp[""]

    with pytest.raises(YellowPagesQueryError, match=r"Cannot tokenize"):
        _ = yp["BPM $$$"]


def test_query_mismatched_parentheses_raise(yp):
    with pytest.raises(YellowPagesQueryError, match=r"Mismatched parentheses"):
        _ = yp["(BPM|HCORR"]


def test_query_invalid_regex_raise(yp):
    with pytest.raises(YellowPagesQueryError, match=r"Invalid regex"):
        _ = yp["re{(}"]
