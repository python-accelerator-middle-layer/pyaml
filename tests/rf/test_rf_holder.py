import pytest

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLException


@pytest.fixture
def design():
    return Accelerator.load("tests/config/EBS_rf_multi.yaml", ignore_external=True).design


def test_rf_holder_getitem_exact_name_matches_get(design):
    assert design.rf["DEFAULT_RF_PLANT"] is design.rf.get("DEFAULT_RF_PLANT")


def test_rf_holder_getitem_exact_name_miss_raises(design):
    with pytest.raises(PyAMLException):
        design.rf["UNKNOWN"]


def test_rf_holder_getitem_wildcard_returns_an_array(design):
    matching = design.rf["DEFAULT_*"]
    assert matching.names() == ["DEFAULT_RF_PLANT"]
    assert design.rf["MISSING*"].names() == []


def test_rf_transmitter_holder_getitem_exact_name_matches_get(design):
    assert design.rf.transmitter["RFTRA1"] is design.rf.transmitter.get("RFTRA1")


def test_rf_transmitter_holder_getitem_exact_name_miss_raises(design):
    with pytest.raises(PyAMLException):
        design.rf.transmitter["UNKNOWN"]


def test_rf_transmitter_holder_getitem_wildcard_returns_an_array(design):
    matching = design.rf.transmitter["RFTRA*"]
    assert sorted(matching.names()) == ["RFTRA1", "RFTRA2", "RFTRA_HARMONIC"]


def test_rf_transmitter_holder_getitem_list_of_patterns(design):
    selected = design.rf.transmitter[["RFTRA1", "RFTRA2"]]
    assert selected.names() == ["RFTRA1", "RFTRA2"]


def test_rf_transmitter_holder_getitem_regex(design):
    matching = design.rf.transmitter["re:^RFTRA[12]$"]
    assert sorted(matching.names()) == ["RFTRA1", "RFTRA2"]
