import pytest

from pyaml.arrays.bpm_array import BPMArray
from pyaml.arrays.element_array import ElementArray
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.bpm.bpm import BPM
from pyaml.common.exception import PyAMLException
from pyaml.lattice.simulator import Simulator


@pytest.fixture
def holder(accelerator_from_fragments, sr_configuration_fragments):
    sr = accelerator_from_fragments(*sr_configuration_fragments)
    sr.design.get_lattice().disable_6d()
    return sr.design


def test_exact_name_returns_the_element_or_none(holder):
    assert holder["BPM_C04-01"] is holder.bpm.get("BPM_C04-01")
    assert holder["UNKNOWN"] is None


def test_get_and_full_slice_keep_registration_order(holder):
    names = [element.get_name() for element in holder.get_all_elements()]

    assert type(holder.get()) is ElementArray
    assert type(holder[:]) is ElementArray
    assert holder.get().names() == names
    assert holder[:].names() == names
    assert names != sorted(names)


def test_collections_are_independent_but_share_elements(holder):
    collection = holder.get()
    first = holder[0]
    original_names = collection.names()

    assert collection[0] is first
    collection.clear()
    assert holder[0] is first
    assert holder.get().names() == original_names


def test_new_calls_reflect_registry_additions(holder):
    previous = holder.get()
    holder.fill_device([BPM("EXTRA_BPM", lattice_names="list(BPM_C04-01)")])

    assert "EXTRA_BPM" not in previous.names()
    assert holder.get().names() == previous.names() + ["EXTRA_BPM"]
    assert holder["EXTRA_BPM"] is holder.bpm.get("EXTRA_BPM")


def test_patterns_always_return_arrays(holder):
    assert isinstance(holder["BPM*"], BPMArray)
    assert holder["BPM*"].names() == ["BPM_C04-01", "BPM_C04-02"]
    assert isinstance(holder["BPM_C04-0[1]"], BPMArray)
    assert holder["BPM_C04-0[1]"].names() == ["BPM_C04-01"]
    assert holder["BPM_C04-0?"].names() == ["BPM_C04-01", "BPM_C04-02"]
    assert type(holder["MISSING*"]) is ElementArray
    assert holder["MISSING*"].names() == []


def test_character_classes_in_name_patterns(holder):
    assert holder["BPM_C04-0[12]"].names() == ["BPM_C04-01", "BPM_C04-02"]
    assert holder["BPM_C04-0[1-2]"].names() == ["BPM_C04-01", "BPM_C04-02"]
    assert holder["SH1A-C01-[HV]*"].names() == ["SH1A-C01-H", "SH1A-C01-V"]
    assert holder["BPM_C04-0[!2]"].names() == ["BPM_C04-01"]


def test_colons_are_part_of_names(holder):
    holder.fill_device([BPM("CELL04:BPM01", lattice_names="list(BPM_C04-01)")])

    assert holder["CELL04:BPM01"] is holder.bpm.get("CELL04:BPM01")
    assert holder["CELL04:BPM*"].names() == ["CELL04:BPM01"]
    assert holder["model_name:*"].names() == []


def test_magnet_subclasses_share_a_typed_array_in_either_order(holder):
    horizontal = holder.magnet.get("SH1A-C01-H")
    vertical = holder.magnet.get("SH1A-C01-V")
    start = holder.get_all_elements().index(horizontal)

    assert type(horizontal) is not type(vertical)
    assert isinstance(holder["SH1A-C01-[HV]"], MagnetArray)
    assert isinstance(holder[start : start + 2], MagnetArray)
    assert isinstance(holder[start + 1 : start - 1 : -1], MagnetArray)
    assert holder[start + 1 : start - 1 : -1].names() == ["SH1A-C01-V", "SH1A-C01-H"]


def test_mixed_selection_returns_a_generic_array(holder):
    selected = holder["*-C01*"]

    assert type(selected) is ElementArray
    assert "QF1A-C01" in selected.names()
    assert "SH1A-C01" in selected.names()


def test_indices_and_slices_follow_insertion_order(holder):
    registered = holder.get_all_elements()

    assert holder[0] is registered[0]
    assert holder[-1] is registered[-1]
    assert list(holder[1:3]) == registered[1:3]
    assert list(holder[::2]) == registered[::2]
    assert isinstance(holder[-2:], BPMArray)
    assert holder[-2:].names() == ["BPM_C04-01", "BPM_C04-02"]
    assert type(holder[len(registered) :]) is ElementArray


def test_empty_holder_returns_empty_collections(ebs_lattice_file):
    holder = Simulator(name="empty", lattice=str(ebs_lattice_file))

    assert type(holder.get()) is ElementArray
    assert holder[:].names() == []
    assert holder["BPM*"].names() == []
    assert holder["BPM_C04-01"] is None


def test_invalid_indices_and_keys_raise_clear_errors(holder):
    size = len(holder.get_all_elements())

    with pytest.raises(IndexError):
        holder[size]
    with pytest.raises(IndexError):
        holder[-size - 1]
    with pytest.raises(TypeError):
        holder[1.5]
    with pytest.raises(ValueError):
        holder[::0]


def test_selection_intersects_with_a_configured_family(holder):
    selected = holder["SH1A-C0?-H"] & holder.get_elements("ElArray")

    assert isinstance(selected, MagnetArray)
    assert selected.names() == ["SH1A-C02-H"]
    assert holder.get_element("SH1A-C02-H") is holder["SH1A-C02-H"]
    assert holder.get_all_elements() == list(holder.get())
    with pytest.raises(PyAMLException):
        holder.get_element("UNKNOWN")


def test_existing_array_field_filters_still_work(holder):
    selected = holder["SH1A-C0?-H"]["model_name:SH1A-C01"]

    assert selected.names() == ["SH1A-C01-H"]


def test_existing_empty_intersection_stays_a_list(holder):
    assert type(holder["SH1A-C0?-H"] & holder["SH1A-C0?-V"]) is list
