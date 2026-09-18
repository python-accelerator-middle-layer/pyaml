import pytest

from pyaml.arrays.element_array import ElementArray
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.common.exception import PyAMLException


@pytest.fixture
def design(accelerator_from_fragments, sr_configuration_fragments):
    sr = accelerator_from_fragments(*sr_configuration_fragments)
    return sr.design


def test_slices_keep_the_common_magnet_type(design):
    magnets = design.magnets.get()
    assert len({type(magnet) for magnet in magnets}) > 1

    assert type(magnets[:]) is MagnetArray
    assert type(magnets[::-1]) is MagnetArray
    assert magnets[:].names() == magnets.names()
    assert magnets[::-1].names() == list(reversed(magnets.names()))
    assert magnets[:][0] is magnets[0]
    assert magnets[:].get_peer() is design


def test_filters_keep_the_common_magnet_type(design):
    magnets = design.magnets.get()
    expected = ["SH1A-C01-H", "SH1A-C01-V", "SH1A-C01-SQ"]

    selected = magnets["SH1A-C01*"]
    by_model = magnets["model_name:SH1A-C01"]

    assert len({type(magnet) for magnet in selected}) > 1
    assert type(selected) is MagnetArray
    assert type(by_model) is MagnetArray
    assert selected.names() == expected
    assert by_model.names() == expected


def test_magnet_holder_selection_uses_the_same_typing(design):
    assert type(design.magnets[:]) is MagnetArray
    assert type(design.magnets["SH*"]) is MagnetArray
    assert design.magnets[:].names() == design.magnets.get().names()


def test_mixed_array_stays_generic_until_only_magnets_are_selected(design):
    mixed = design.get_elements("ElArray")

    assert type(mixed[:]) is ElementArray
    assert mixed[:].names() == mixed.names()
    assert type(mixed["SH*"]) is MagnetArray
    assert mixed["SH*"].names() == ["SH1A-C01-V", "SH1A-C02-H"]


def test_empty_selections_and_integer_indexing_keep_their_behavior(design):
    magnets = design.magnets.get()

    assert type(magnets[0:0]) is ElementArray
    assert magnets[0:0] == []
    assert type(magnets["UNKNOWN*"]) is ElementArray
    assert magnets["UNKNOWN*"] == []
    assert magnets[0] is design.magnet.get(magnets.names()[0])
    assert type(magnets - magnets) is list


def test_literal_name_miss_raises(design):
    magnets = design.magnets.get()

    with pytest.raises(PyAMLException):
        magnets["UNKNOWN"]
    with pytest.raises(PyAMLException):
        design.magnets["UNKNOWN"]


def test_literal_name_hit_still_returns_a_single_element_array(design):
    magnets = design.magnets.get()

    selected = magnets["SH1A-C01-H"]
    assert type(selected) is MagnetArray
    assert selected.names() == ["SH1A-C01-H"]


def test_bracket_only_pattern_is_a_wildcard(design):
    magnets = design.magnets.get()
    assert sorted(magnets["SH1A-C0[12]-H"].names()) == ["SH1A-C01-H", "SH1A-C02-H"]


def test_regex_pattern_is_supported(design):
    magnets = design.magnets.get()
    assert sorted(magnets["re:^SH1A-C0[12]-H$"].names()) == ["SH1A-C01-H", "SH1A-C02-H"]


def test_list_of_patterns_is_supported(design):
    magnets = design.magnets.get()
    selected = magnets[["SH1A-C01-H", "SH1A-C02-H"]]
    assert selected.names() == ["SH1A-C01-H", "SH1A-C02-H"]


def test_wildcard_matching_is_case_sensitive(design):
    magnets = design.magnets.get()
    assert magnets["sh1a*"] == []
