"""
A serialized family used like one simple magnet.

What is a serialized family?
    N magnets wired on ONE power supply (see test_serialized_magnets_expected_behaviour.py).
    The family itself is a Magnet: family.strength is the average strength of the series,
    family.hardware is the current of the power supply.

What happens in a magnet array?
    The family name adds ONE element to the array: the family. Its magnets are not added, they
    are already driven through the family. Excluding the family also excludes its magnets, and
    excluding one magnet of a family which is in the array raises an error (a series cannot be
    split).

The family is also a container of its magnets: len(family), for magnet in family, family[i],
family["name"], family.names() and family.magnets (a MagnetArray of its magnets).
"""

import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.magnet.inline_curve import InlineCurve
from pyaml.magnet.linear_serialized_model import LinearSerializedMagnetModel
from pyaml.magnet.magnet import Magnet
from pyaml.magnet.serialized_magnet import SerializedMagnets

# QF1A (4 magnets) and QD2A (3 magnets) are serialized families, QF1E-C04 has its own power supply
CONFIG = "tests/config/sr_serialized_magnets_cs.yaml"
TANGO_DUMMY = [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}]
MODES = ["design", "live"]


def load(mode: str):
    """Load the configuration and return the holder of the requested mode (simulator or control system)."""
    sr = Accelerator.load(CONFIG)
    return getattr(sr, mode)


# ---------------------------------------------------------------------------
# The family is a magnet and a container of its magnets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_is_a_magnet_driving_its_whole_series(install_test_package, mode):
    holder = load(mode)
    family = holder.serialized_magnet.get("QF1A")

    # The family can be used wherever a magnet is expected
    assert isinstance(family, Magnet)

    # It drives the whole series: it is not one magnet of the series
    assert family.series_index is None
    assert holder.magnet.get("QF1A-C06").series_index == 1


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_gives_access_to_its_magnets(install_test_package, mode):
    holder = load(mode)
    family = holder.serialized_magnet.get("QF1A")
    magnets = family.get_magnets()

    # Number and names of the magnets, in the order of the configuration
    assert len(family) == 4
    assert family.names() == ["QF1A-C05", "QF1A-C06", "QF1A-C07", "QF1A-C08"]

    # Iterating gives the magnets attached to the same simulator or control system as the family
    assert list(family) == magnets
    assert all(m.peer is holder for m in family)

    # One magnet by position or by name: the same object as holder.magnet.get(name)
    assert family[1] is magnets[1]
    assert family["QF1A-C07"] is holder.magnet.get("QF1A-C07")

    # A slice gives a magnet array
    assert family[1:3].names() == ["QF1A-C06", "QF1A-C07"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_rejects_a_name_outside_the_series(install_test_package, mode):
    family = load(mode).serialized_magnet.get("QF1A")

    with pytest.raises(PyAMLException, match="QD2A-C05 is not a magnet of the serialized family QF1A"):
        family["QD2A-C05"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_magnets_is_a_magnet_array_of_the_series(install_test_package, mode):
    family = load(mode).serialized_magnet.get("QF1A")
    family.hardware.set(80.0)

    # family.magnets is a regular magnet array, named after the family
    assert isinstance(family.magnets, MagnetArray)
    assert family.magnets.get_name() == "QF1A"
    assert family.magnets.names() == family.names()

    # It reads the strength of each magnet, like family.strengths
    assert np.allclose(family.magnets.strengths.get(), family.strengths.get())


def test_configured_family_iterates_on_its_virtual_magnets():
    # A family built from the configuration, not attached to a simulator or a control system
    model = LinearSerializedMagnetModel(
        curves=InlineCurve(mat=np.array([[0.0, 0.0], [100.0, 1.0]])),
        calibration_factors=1.0,
        calibration_offsets=0.0,
        unit="m-1",
        hardware_unit="A",
        powerconverter="the/power/supply",
    )
    family = SerializedMagnets(name="FAMILY", function="B1", elements=["M1", "M2"], model=model)

    # Its magnets are the virtual magnets of the configuration
    assert [m.get_name() for m in family] == ["M1", "M2"]

    # They are not attached: reading them raises, as for any magnet not attached
    with pytest.raises(PyAMLException, match="not attached"):
        family[0].strength.get()


# ---------------------------------------------------------------------------
# Family names in a magnet array
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_name_adds_the_family_as_one_magnet(install_test_package, mode):
    holder = load(mode)

    holder.magnets.add("ARRAY", ["QF1A"])
    array = holder.magnets.get("ARRAY")

    # One element: the family itself
    assert array.names() == ["QF1A"]
    assert array[0] is holder.serialized_magnet.get("QF1A")


@pytest.mark.parametrize(
    "elements, expected",
    [
        # The family and one of its magnets: the magnet is already driven by the family
        (["QF1A", "QF1A-C06"], ["QF1A"]),
        # Same thing when the magnet comes first
        (["QF1A-C06", "QF1A"], ["QF1A"]),
        # A wildcard matching the family and its magnets: only the family is kept,
        # QF1E-C04 has its own power supply and is kept too
        (["QF1*"], ["QF1A", "QF1E-C04"]),
        # The magnets of a family which is not in the array are added as usual
        (["QD2A-C05", "QF1A"], ["QD2A-C05", "QF1A"]),
    ],
)
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_magnets_of_a_family_in_the_array_are_not_added(install_test_package, mode, elements, expected):
    holder = load(mode)

    holder.magnets.add("ARRAY", elements)

    assert holder.magnets.get("ARRAY").names() == expected


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_excluding_a_family_excludes_its_magnets(install_test_package, mode):
    holder = load(mode)

    # Every magnet of QF1A and QD2A, then QF1A is excluded: only the magnets of QD2A remain
    holder.magnets.add("ARRAY", ["QF1A-C*", "QD2A-C*", "~QF1A"])

    assert holder.magnets.get("ARRAY").names() == ["QD2A-C05", "QD2A-C06", "QD2A-C07"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_excluding_a_magnet_of_a_family_in_the_array_raises(install_test_package, mode):
    holder = load(mode)

    # QF1A drives QF1A-C05: the series cannot be split
    with pytest.raises(PyAMLException, match="QF1A-C05 cannot be excluded, it is driven by QF1A"):
        holder.magnets.add("ARRAY", ["QF1A", "~QF1A-C05"])


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_lone_exclusion_gives_an_empty_array(install_test_package, mode):
    holder = load(mode)

    # Nothing is included, so nothing is left
    holder.magnets.add("ARRAY", ["~QF1A"])

    assert len(holder.magnets.get("ARRAY")) == 0


@pytest.mark.parametrize("elements", [["QF1A-C05", "QF1A-C05"], ["QF1A", "QF1A"]])
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_name_listed_twice_still_raises(install_test_package, mode, elements):
    holder = load(mode)

    with pytest.raises(PyAMLException, match="duplicate name"):
        holder.magnets.add("ARRAY", elements)


# ---------------------------------------------------------------------------
# Reading and writing an array holding families
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_array_reads_the_average_strength_of_each_family(install_test_package, mode):
    holder = load(mode)
    qf1a, qd2a = holder.serialized_magnet.get("QF1A"), holder.serialized_magnet.get("QD2A")
    quad = holder.magnet.get("QF1E-C04")
    qf1a.hardware.set(80.0)
    qd2a.hardware.set(20.0)
    quad.hardware.set(50.0)

    holder.magnets.add("ARRAY", ["QF1A", "QD2A", "QF1E-C04"])
    array = holder.magnets.get("ARRAY")

    # One value per element: the average strength of each family, the strength of the quadrupole
    assert np.allclose(array.strengths.get(), [qf1a.strength.get(), qd2a.strength.get(), quad.strength.get()])
    # One current per element: the current of each power supply
    assert np.allclose(array.hardwares.get(), [80.0, 20.0, 50.0])


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_array_writes_each_family_like_its_own_strength(install_test_package, mode):
    holder = load(mode)
    qf1a, qd2a = holder.serialized_magnet.get("QF1A"), holder.serialized_magnet.get("QD2A")
    quad = holder.magnet.get("QF1E-C04")
    qf1a.hardware.set(80.0)
    qd2a.hardware.set(20.0)
    holder.magnets.add("ARRAY", ["QF1A", "QD2A", "QF1E-C04"])
    array = holder.magnets.get("ARRAY")

    # Ask for new strengths: each family gets the current giving this average strength,
    # exactly as family.strength.set() would do
    requested = array.strengths.get() * 1.01
    expected_qf1a = qf1a.strength.hardware_from_strength(requested[0], qf1a.hardware.get())
    expected_qd2a = qd2a.strength.hardware_from_strength(requested[1], qd2a.hardware.get())
    array.strengths.set(requested)

    assert qf1a.hardware.get() == pytest.approx(expected_qf1a)
    assert qd2a.hardware.get() == pytest.approx(expected_qd2a)
    assert quad.strength.get() == pytest.approx(requested[2])
    assert np.allclose(array.strengths.get(), requested)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_array_set_of_get_does_not_change_the_machine(install_test_package, mode):
    holder = load(mode)
    qf1a, qd2a = holder.serialized_magnet.get("QF1A"), holder.serialized_magnet.get("QD2A")
    quad = holder.magnet.get("QF1E-C04")
    qf1a.hardware.set(80.0)
    qd2a.hardware.set(20.0)
    quad.hardware.set(50.0)
    holder.magnets.add("ARRAY", ["QF1A", "QD2A", "QF1E-C04"])
    array = holder.magnets.get("ARRAY")

    # Writing back what was read keeps every power supply where it was
    array.strengths.set(array.strengths.get())

    assert qf1a.hardware.get() == pytest.approx(80.0)
    assert qd2a.hardware.get() == pytest.approx(20.0)
    assert quad.hardware.get() == pytest.approx(50.0)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_selections_holding_families_are_magnet_arrays(install_test_package, mode):
    holder = load(mode)
    holder.magnets.add("ARRAY", ["QF1A", "QD2A", "QF1E-C04"])
    array = holder.magnets.get("ARRAY")

    # Families and a magnet, or families only: both are magnet arrays
    assert isinstance(array[0:3], MagnetArray)
    families_only = array.of_type(SerializedMagnets)
    assert isinstance(families_only, MagnetArray)
    assert families_only.names() == ["QF1A", "QD2A"]


def test_family_mixing_functions_has_no_average_strength_in_an_array():
    sr = Accelerator.load("tests/config/sr_serialized_magnets.yaml", include_locations=False, ignore_external=True)

    # mixedFunctionSeries holds a quadrupole and a sextupole
    sr.design.magnets.add("ARRAY", ["mixedFunctionSeries"])
    array = sr.design.magnets.get("ARRAY")

    # Its current is defined, its average strength is not
    assert len(array.hardwares.get()) == 1
    with pytest.raises(PyAMLException, match="mixing magnet functions"):
        array.strengths.get()


# ---------------------------------------------------------------------------
# Families in configured magnet arrays
# ---------------------------------------------------------------------------


def test_configured_magnet_array_matching_families_is_used_by_the_tune_tool():
    sr = Accelerator.load("tests/config/sr_serialized_magnets.yaml", include_locations=False, ignore_external=True)

    # QForTune is a pyaml.arrays.magnet with the patterns QD2? and QF1?, which match 4 families
    quads = sr.design.magnets.get("QForTune")
    assert quads.names() == ["QD2A", "QD2E", "QF1A", "QF1E"]

    # The tune tool finds it as a regular magnet array: one knob per power supply
    tool = sr.design.tool.get("DEFAULT_TUNE_RESPONSE_MATRIX")
    assert tool.quadrupoles is quads
