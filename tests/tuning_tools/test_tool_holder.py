import pytest

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLException


@pytest.fixture
def design():
    return Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design


def test_tool_holder_getitem_exact_name_matches_get(design):
    assert design.tool["DEFAULT_TUNE_CORRECTION"] is design.tool.get("DEFAULT_TUNE_CORRECTION")


def test_tool_holder_getitem_exact_name_miss_raises(design):
    with pytest.raises(PyAMLException):
        design.tool["UNKNOWN"]


def test_tool_holder_getitem_wildcard_returns_an_array(design):
    matching = design.tool["DEFAULT_TUNE*"]
    assert sorted(matching.names()) == ["DEFAULT_TUNE_CORRECTION", "DEFAULT_TUNE_RESPONSE_MATRIX"]
    assert design.tool["MISSING*"].names() == []


def test_tool_holder_getitem_list_of_patterns(design):
    selected = design.tool[["DEFAULT_TUNE_CORRECTION", "DEFAULT_ORBIT_CORRECTION"]]
    assert selected.names() == ["DEFAULT_TUNE_CORRECTION", "DEFAULT_ORBIT_CORRECTION"]


def test_tool_holder_getitem_regex(design):
    matching = design.tool["re:^DEFAULT_(TUNE|ORBIT)_CORRECTION$"]
    assert sorted(matching.names()) == ["DEFAULT_ORBIT_CORRECTION", "DEFAULT_TUNE_CORRECTION"]
