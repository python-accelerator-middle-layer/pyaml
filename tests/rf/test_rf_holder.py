import copy

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


def test_rf_transmitter_holder_getitem_list_selection_ignores_request_order(design):
    """A list-of-patterns selection lands in configuration order, whatever order the names
    were requested in, same as every other holder (see
    test_every_accessor_returns_a_list_selection_in_configuration_order)."""
    forward = design.rf.transmitter[["RFTRA1", "RFTRA2"]]
    backward = design.rf.transmitter[["RFTRA2", "RFTRA1"]]
    assert forward.names() == backward.names() == ["RFTRA1", "RFTRA2"]


def test_rf_holder_getitem_list_selection_ignores_request_order(design):
    """Same configuration-order guarantee as the RF transmitter holder, at the RF plant level.

    Only one RF plant is registered by this fixture, so a distinct second entry is poked
    directly into the store (a renamed copy of the existing plant) to make request order and
    configuration order observably different.
    """
    spare_plant = copy.copy(design.rf.get("DEFAULT_RF_PLANT"))
    spare_plant._name = "SPARE_RF_PLANT"
    design._RFPLANT["SPARE_RF_PLANT"] = spare_plant

    forward = design.rf[["DEFAULT_RF_PLANT", "SPARE_RF_PLANT"]]
    backward = design.rf[["SPARE_RF_PLANT", "DEFAULT_RF_PLANT"]]
    assert forward.names() == backward.names() == ["DEFAULT_RF_PLANT", "SPARE_RF_PLANT"]


def test_rf_transmitter_holder_getitem_regex(design):
    matching = design.rf.transmitter["re:^RFTRA[12]$"]
    assert sorted(matching.names()) == ["RFTRA1", "RFTRA2"]
