# tests/test_yellow_pages.py
#
# Self-contained tests for fully dynamic YellowPages.
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


class _Array:
    """Minimal array-like object exposing names and a stable module path."""

    __module__ = "pyaml.arrays.test_array"

    def __init__(self, names):
        self._names = list(names)

    def __len__(self):
        return len(self._names)

    def __iter__(self):
        return iter(self._names)


class _Tool:
    """Minimal tool-like object exposing a stable module path."""

    __module__ = "pyaml.tuning_tools.test_tool"


class _Diagnostic:
    """Minimal diagnostic-like object exposing a stable module path."""

    __module__ = "pyaml.diagnostics.test_diagnostic"


class _Holder:
    """Minimal ElementHolder double with discovery + resolution."""

    def __init__(self, arrays=None, tools=None, diagnostics=None):
        self._arrays = dict(arrays or {})
        self._tools = dict(tools or {})
        self._diagnostics = dict(diagnostics or {})

    # Discovery
    def _list_arrays(self) -> list[str]:
        return list(self._arrays.keys())

    def _list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def _list_diagnostics(self) -> list[str]:
        return list(self._diagnostics.keys())

    # Resolution
    def _get_array(self, name: str):
        if name not in self._arrays:
            raise KeyError(name)
        return self._arrays[name]

    def _get_tool(self, name: str):
        if name not in self._tools:
            raise KeyError(name)
        return self._tools[name]

    def _get_diagnostic(self, name: str):
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
            "BPM": _Array(["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"]),
            "HCORR": _Array(["CH_C01-01", "CH_C01-02"]),
        },
        tools={"DEFAULT_ORBIT_CORRECTION": _Tool()},
        diagnostics={"DEFAULT_BETATRON_TUNE_MONITOR": _Diagnostic()},
    )

    tango = _Holder(
        arrays={
            "BPM": _Array(["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"]),
            # HCORR intentionally missing in tango
        },
        tools={},
        diagnostics={},
    )

    # Simulators
    design = _Holder(
        arrays={
            "BPM": _Array(["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"]),
            "HCORR": _Array(["CH_C01-01"]),
        },
        tools={"DEFAULT_ORBIT_CORRECTION": _Tool()},
        diagnostics={},
    )

    return _Accelerator(
        controls={"live": live, "tango": tango},
        simulators={"design": design},
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


def test_get_object_without_mode_returns_only_available_modes(yp):
    hcorr = yp._get_object("HCORR")
    assert set(hcorr.keys()) == {"live", "design"}


def test_get_object_with_mode_returns_object_or_raises(yp):
    bpm_live = yp._get_object("BPM", mode="live")
    assert len(bpm_live) == 3

    with pytest.raises(YellowPagesError, match=r"Unknown mode"):
        yp._get_object("BPM", mode="does_not_exist")

    with pytest.raises(YellowPagesError, match=r"not available in mode 'tango'"):
        yp._get_object("HCORR", mode="tango")


def test_availability(yp):
    assert yp.availability("BPM") == {"live", "tango", "design"}
    assert yp.availability("HCORR") == {"live", "design"}


# ---------------------------
# Query API (public get + __getitem__)
# ---------------------------


def test_get_and_getitem_are_equivalent_for_wildcards(yp):
    assert yp.get("BPM_C01*") == yp["BPM_C01*"]


def test_get_and_getitem_are_equivalent_for_regex(yp):
    assert yp.get("re:^BPM_C01-0[12]$") == yp["re:^BPM_C01-0[12]$"]


def test_unknown_key_errors(yp):
    with pytest.raises(KeyError, match=r"Unknown YellowPages key"):
        yp._get_object("DOES_NOT_EXIST")


# ---------------------------
# __repr__ formatting (controls/simulators + types + sizes + modes)
# ---------------------------


def test_repr_has_controls_and_simulators_headers(yp):
    s = repr(yp)

    assert "Controls:" in s
    assert "Simulators:" in s

    assert re.search(r"^\s+live$", s, re.M) is not None
    assert re.search(r"^\s+tango$", s, re.M) is not None
    assert re.search(r"^\s+design$", s, re.M) is not None


def test_repr_array_size_compaction_when_identical_everywhere(yp):
    s = repr(yp)
    bpm_line = next(line for line in s.splitlines() if line.strip().startswith("BPM"))
    assert "(pyaml.arrays.test_array)" in bpm_line
    assert "size=3" in bpm_line
    assert "size={" not in bpm_line


def test_repr_array_size_dict_when_different_or_not_everywhere(yp):
    s = repr(yp)
    hcorr_line = next(line for line in s.splitlines() if line.strip().startswith("HCORR"))
    assert "(pyaml.arrays.test_array)" in hcorr_line
    assert "size={" in hcorr_line
    assert "live:2" in hcorr_line
    assert "design:1" in hcorr_line
    assert "modes=" in hcorr_line
    assert "missing=" in hcorr_line


def test_repr_tools_show_type_and_modes_missing(yp):
    s = repr(yp)
    tool_line = next(line for line in s.splitlines() if "DEFAULT_ORBIT_CORRECTION" in line)
    assert "(pyaml.tuning_tools.test_tool)" in tool_line
    assert "modes=" in tool_line
    assert "missing=" in tool_line


def test_repr_diagnostics_show_type(yp):
    s = repr(yp)
    diag_line = next(line for line in s.splitlines() if "DEFAULT_BETATRON_TUNE_MONITOR" in line)
    assert "(pyaml.diagnostics.test_diagnostic)" in diag_line


# ---------------------------
# Query language (wildcard + regex)
# ---------------------------


def test_query_wildcard(yp):
    out = yp["BPM_C01*"]
    assert out == ["BPM_C01-01", "BPM_C01-02"]


def test_query_regex(yp):
    out = yp["re:^BPM_C01-0[12]$"]
    assert out == ["BPM_C01-01", "BPM_C01-02"]


def test_query_regex_alone_filters_all_known_ids(yp):
    out = yp["re:^BPM_"]
    assert out == ["BPM_C01-01", "BPM_C01-02", "BPM_C02-01"]


def test_query_wildcard_on_hcorr(yp):
    out = yp["CH_C01*"]
    assert out == ["CH_C01-01", "CH_C01-02"]


def test_query_empty_raises(yp):
    with pytest.raises(YellowPagesQueryError, match=r"Empty YellowPages query"):
        _ = yp[""]


def test_query_invalid_regex_raise(yp):
    with pytest.raises(YellowPagesQueryError, match=r"Invalid regex"):
        _ = yp["re:("]


def test_query_with_mode_wildcard(yp):
    out = yp.get("CH_C01*", mode="live")
    assert out == ["CH_C01-01", "CH_C01-02"]


def test_query_with_mode_regex(yp):
    out = yp.get("re:^BPM_C01", mode="design")
    assert out == ["BPM_C01-01", "BPM_C01-02"]


def test_query_with_unknown_mode(yp):
    with pytest.raises(YellowPagesError, match=r"Unknown mode"):
        yp.get("BPM*", mode="invalid")
