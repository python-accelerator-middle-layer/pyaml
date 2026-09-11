import pytest

from pyaml.arrays.element_array import ElementArray
from pyaml.arrays.magnet_array import MagnetArray


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
