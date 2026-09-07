import pytest

from pyaml.arrays.bpm_array import BPMArray
from pyaml.arrays.element_array import ElementArray
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.bpm.bpm import BPM
from pyaml.common.element import Element
from pyaml.common.exception import PyAMLException
from pyaml.common.holders.element_holder import ElementHolder
from pyaml.magnet.magnet import Magnet


class CollectionHolder(ElementHolder):
    """Minimal holder for collection examples, without device access."""

    def __init__(self, *elements):
        super().__init__()
        for element in elements:
            element._peer = self
            self.add_element(element)

    def create_magnet_strength_aggregator(self, magnets):
        return None

    def create_magnet_hardware_aggregator(self, magnets):
        return None

    def create_bpm_aggregators(self, bpms):
        return [None, None, None]


class Quadrupole(Magnet):
    pass


class Corrector(Magnet):
    pass


def test_exact_name_returns_the_element_or_none():
    bpm = BPM("BPM01")
    holder = CollectionHolder(bpm)

    assert holder["BPM01"] is bpm
    assert holder["UNKNOWN"] is None


def test_get_and_full_slice_keep_registration_order():
    holder = CollectionHolder(BPM("BPM02"), BPM("BPM01"))

    assert type(holder.get()) is ElementArray
    assert type(holder[:]) is ElementArray
    assert holder.get().names() == ["BPM02", "BPM01"]
    assert holder[:].names() == ["BPM02", "BPM01"]


def test_collections_are_independent_but_share_elements():
    bpm = BPM("BPM01")
    holder = CollectionHolder(bpm)
    collection = holder.get()

    assert collection[0] is bpm
    collection.clear()
    assert holder["BPM01"] is bpm
    assert holder.get().names() == ["BPM01"]


def test_new_calls_reflect_registry_additions():
    holder = CollectionHolder(BPM("BPM01"))
    previous = holder.get()
    added = BPM("BPM02").attach(holder, None, None, None)
    holder.add_element(added)

    assert previous.names() == ["BPM01"]
    assert holder.get().names() == ["BPM01", "BPM02"]


def test_patterns_always_return_arrays():
    holder = CollectionHolder(BPM("BPM02"), BPM("BPM01"), Element("MARKER"))

    assert isinstance(holder["BPM*"], BPMArray)
    assert holder["BPM*"].names() == ["BPM02", "BPM01"]
    assert isinstance(holder["BPM0[1]"], BPMArray)
    assert holder["BPM0[1]"].names() == ["BPM01"]
    assert holder["BPM0?"].names() == ["BPM02", "BPM01"]
    assert type(holder["MISSING*"]) is ElementArray
    assert holder["MISSING*"].names() == []


def test_character_classes_in_name_patterns():
    holder = CollectionHolder(
        BPM("BPM01"),
        BPM("BPM02"),
        BPM("BPM03"),
        BPM("BPM04"),
        Magnet("QF01"),
        Magnet("QD01"),
        Magnet("QS01"),
    )

    assert holder["BPM0[123]"].names() == ["BPM01", "BPM02", "BPM03"]
    assert holder["BPM0[1-3]"].names() == ["BPM01", "BPM02", "BPM03"]
    assert holder["Q[FD]*"].names() == ["QF01", "QD01"]
    assert holder["BPM0[!3]"].names() == ["BPM01", "BPM02", "BPM04"]


def test_colons_are_part_of_names():
    bpm = BPM("CELL01:BPM01")
    holder = CollectionHolder(bpm, Magnet("MAGNET"))

    assert holder["CELL01:BPM01"] is bpm
    assert holder["CELL01:BPM*"].names() == ["CELL01:BPM01"]
    assert holder["model_name:*"].names() == []


def test_magnet_subclasses_share_a_typed_array_in_either_order():
    holder = CollectionHolder(Quadrupole("MAG_Q"), Corrector("MAG_C"))

    assert isinstance(holder["MAG*"], MagnetArray)
    assert isinstance(holder[::-1], MagnetArray)
    assert holder[::-1].names() == ["MAG_C", "MAG_Q"]


def test_mixed_selection_returns_a_generic_array():
    holder = CollectionHolder(Magnet("CELL_Q"), BPM("CELL_BPM"))

    assert type(holder["CELL*"]) is ElementArray
    assert holder["CELL*"].names() == ["CELL_Q", "CELL_BPM"]


def test_indices_and_slices_follow_insertion_order():
    second = BPM("BPM02")
    first = BPM("BPM01")
    third = BPM("BPM03")
    holder = CollectionHolder(second, first, third)

    assert holder[0] is second
    assert holder[-1] is third
    assert isinstance(holder[1:3], BPMArray)
    assert holder[1:3].names() == ["BPM01", "BPM03"]
    assert holder[::2].names() == ["BPM02", "BPM03"]
    assert type(holder[3:]) is ElementArray


def test_empty_holder_returns_empty_collections():
    holder = CollectionHolder()

    assert type(holder.get()) is ElementArray
    assert holder[:].names() == []
    assert holder["BPM*"].names() == []
    assert holder["BPM01"] is None


def test_invalid_indices_and_keys_raise_clear_errors():
    holder = CollectionHolder(BPM("BPM01"))

    with pytest.raises(IndexError):
        holder[1]
    with pytest.raises(IndexError):
        holder[-2]
    with pytest.raises(TypeError):
        holder[1.5]
    with pytest.raises(ValueError):
        holder[::0]


def test_selection_intersects_with_a_configured_family():
    holder = CollectionHolder(Magnet("Q02"), Magnet("Q01"), BPM("BPM01"))
    holder.fill_element_array("CELL01", ["Q01", "BPM01"])

    selected = holder["Q*"] & holder.get_elements("CELL01")

    assert isinstance(selected, MagnetArray)
    assert selected.names() == ["Q01"]
    assert holder.get_element("Q01") is holder["Q01"]
    assert holder.get_all_elements() == list(holder.get())
    with pytest.raises(PyAMLException):
        holder.get_element("UNKNOWN")


def test_existing_array_field_filters_still_work():
    magnet = Magnet("VIRTUAL_Q")
    magnet.set_model_name("PHYSICAL_Q")
    holder = CollectionHolder(magnet)

    assert holder["VIRTUAL*"]["model_name:PHYSICAL*"].names() == ["VIRTUAL_Q"]


def test_existing_empty_intersection_stays_a_list():
    holder = CollectionHolder(Magnet("Q01"), Magnet("Q02"))

    assert type(holder["Q0[1]"] & holder["Q0[2]"]) is list
