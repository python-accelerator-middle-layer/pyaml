"""
Knobs of a tuning tool: one per independent power supply.

A tuning tool acts on power supplies. The magnets of a series share one power supply, so they form ONE knob: their
serialized family, driven through its average strength. knobs_of(array) replaces each magnet of a series by its
family, keeps the other magnets, and keeps the order of first appearance.
"""

import re

import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.tuning_tools.knobs import knobs_of
from pyaml.tuning_tools.response_matrix_data import ResponseMatrixData

# QF1A (4 magnets) and QD2A (3 magnets) are serialized families, QF1E-C04 has its own power supply
CONFIG = "tests/config/sr_serialized_magnets_cs.yaml"
TANGO_DUMMY = [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}]
MODES = ["design", "live"]


def load(mode: str):
    """Load the configuration and return the holder of the requested mode (simulator or control system)."""
    sr = Accelerator.load(CONFIG)
    return getattr(sr, mode)


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
@pytest.mark.parametrize("nb_members", [1, 2, 3, 4])
def test_magnets_of_a_series_give_one_knob_named_after_the_family(install_test_package, mode, nb_members):
    holder = load(mode)
    family = holder.serialized_magnet.get("QF1A")
    quad = holder.magnet.get("QF1E-C04")

    # The individual quad, then the first magnets of the series
    array = MagnetArray("QUADS", [quad, *family.get_magnets()[:nb_members]])
    knobs = knobs_of(array)

    # However many magnets of the series are listed, the series is one knob: the family
    assert knobs.names() == ["QF1E-C04", "QF1A"]
    assert knobs[1] is family
    assert knobs.get_name() == "QUADS"


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_knob_sits_at_the_first_magnet_of_its_series(install_test_package, mode):
    holder = load(mode)
    family = holder.serialized_magnet.get("QF1A")
    quad = holder.magnet.get("QF1E-C04")

    # A magnet of the series, the individual quad, another magnet of the series
    array = MagnetArray("QUADS", [family[2], quad, family[0]])

    assert knobs_of(array).names() == ["QF1A", "QF1E-C04"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_name_gives_the_same_knobs_as_its_magnets(install_test_package, mode):
    holder = load(mode)
    family = holder.serialized_magnet.get("QF1A")
    quad = holder.magnet.get("QF1E-C04")

    by_magnets = knobs_of(MagnetArray("BY_MAGNETS", [quad, *family.get_magnets()]))
    by_family = knobs_of(MagnetArray("BY_FAMILY", [quad, family]))

    assert by_magnets.names() == by_family.names() == ["QF1E-C04", "QF1A"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_two_series_give_two_knobs(install_test_package, mode):
    holder = load(mode)

    # The configured array lists the magnets of both series by wildcard
    knobs = knobs_of(holder.magnets.get("ALL_SERIALIZED"))

    assert knobs.names() == ["QF1A", "QD2A"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_array_without_magnet_of_a_series_is_its_own_knob_array(install_test_package, mode):
    holder = load(mode)
    family = holder.serialized_magnet.get("QF1A")
    quad = holder.magnet.get("QF1E-C04")

    # A family listed by name and an individual quad: nothing to group, the array itself is returned
    array = MagnetArray("QUADS", [family, quad])

    assert knobs_of(array) is array


def test_virtual_magnets_of_a_combined_function_magnet_are_knobs():
    sr = Accelerator.load("tests/config/EBSOrbit.yaml")
    hcorr = sr.design.magnets.get("HCorr")

    # Each corrector of a combined-function magnet is driven on its own: one knob per virtual magnet
    assert knobs_of(hcorr) is hcorr


def test_multipoles_of_a_combined_function_magnet_with_a_matrix_are_strength_knobs():
    sr = Accelerator.load("tests/config/EBSOrbit.yaml")
    design = sr.design
    # SH1A-C04: 4 multipoles (H, V, SQ, S) driven by 5 power supplies through a matrix
    cfm = design.combined_function_magnet.get("SH1A-C04")
    array = MagnetArray("SH1A-C04_CORRECTORS", [design.magnet.get("SH1A-C04-H"), design.magnet.get("SH1A-C04-V")])
    knobs = knobs_of(array)
    cfm.strengths.set(np.array([1e-5, -2e-5, 1e-3, cfm.strengths.get()[3]]))
    power_supplies = cfm.hardwares.get()
    strengths = cfm.strengths.get()

    # One knob per multipole, written through its strength
    assert knobs is array
    knobs.strengths.set(knobs.strengths.get())
    np.testing.assert_allclose(cfm.hardwares.get(), power_supplies)
    np.testing.assert_allclose(cfm.strengths.get(), strengths)

    # A multipole has no power supply of its own: the state of the magnet is the vector of its power supplies
    assert len(power_supplies) == 5
    with pytest.raises(PyAMLException, match="has no model that supports hardware units"):
        knobs.hardwares.get()


def test_series_mixing_magnet_functions_cannot_be_a_knob():
    sr = Accelerator.load("tests/config/sr_serialized_magnets.yaml")
    family = sr.design.serialized_magnet.get("mixedFunctionSeries")

    with pytest.raises(PyAMLException, match="mixedFunctionSeries mixes magnet functions"):
        knobs_of(MagnetArray("MIXED", [family[0]]))
    with pytest.raises(PyAMLException, match="mixedFunctionSeries mixes magnet functions"):
        knobs_of(MagnetArray("MIXED", [family]))


# ---------------------------------------------------------------------------
# Reading and writing the knobs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_knobs_set_of_get_does_not_change_the_machine(install_test_package, mode):
    holder = load(mode)
    qf1a = holder.serialized_magnet.get("QF1A")
    qd2a = holder.serialized_magnet.get("QD2A")
    quad = holder.magnet.get("QF1E-C04")
    qf1a.hardware.set(80.0)
    qd2a.hardware.set(20.0)
    quad.hardware.set(50.0)
    knobs = knobs_of(MagnetArray("QUADS", [qf1a[0], quad, *qd2a.get_magnets(), qf1a[3]]))

    # Through the strengths (excitation curves) and through the power supplies (exact)
    knobs.strengths.set(knobs.strengths.get())
    knobs.hardwares.set(knobs.hardwares.get())

    assert np.allclose(knobs.hardwares.get(), [80.0, 50.0, 20.0])
    assert qf1a.hardware.get() == pytest.approx(80.0)
    assert qd2a.hardware.get() == pytest.approx(20.0)
    assert quad.hardware.get() == pytest.approx(50.0)


@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_knobs_write_the_power_supply_of_a_series_once(install_test_package, monkeypatch):
    from tango.pyaml.attribute import Attribute

    holder = load("live")
    family = holder.serialized_magnet.get("QF1A")
    family.hardware.set(80.0)
    knobs = knobs_of(MagnetArray("QF1A_MAGNETS", family.get_magnets()))

    # Record every write to a device of the dummy control system
    writes = []
    original_set = Attribute.set

    def spy(self, value):
        writes.append(self.name())
        original_set(self, value)

    monkeypatch.setattr(Attribute, "set", spy)

    knobs.strengths.set(knobs.strengths.get() * 1.01)

    # One write, to the power supply of the series
    assert len(writes) == 1
    assert writes[0].endswith("srmag/ps-qf1a/series/current")


# ---------------------------------------------------------------------------
# Response matrix columns against the knobs
# ---------------------------------------------------------------------------


def test_response_matrix_matching_the_knobs_passes_the_check():
    data = ResponseMatrixData(matrix=[[1.0, 2.0], [3.0, 4.0]], observable_names=["x", "y"], variable_names=["A", "B"])

    assert data.check_variables(["A", "B"]) is None


@pytest.mark.parametrize(
    "names, message",
    [
        (["A"], "unexpected \\['B'\\]"),
        (["A", "B", "C"], "missing \\['C'\\]"),
        (["B", "A"], "same variables in another order"),
    ],
)
def test_response_matrix_not_matching_the_knobs_is_described(names, message):
    data = ResponseMatrixData(matrix=[[1.0, 2.0], [3.0, 4.0]], observable_names=["x", "y"], variable_names=["A", "B"])

    difference = data.check_variables(names)

    assert difference is not None
    assert re.search(message, difference)


def test_response_matrix_without_variable_names_is_checked_on_its_columns():
    data = ResponseMatrixData(matrix=[[1.0, 2.0], [3.0, 4.0]], observable_names=["x", "y"])

    assert data.check_variables(["A", "B"]) is None
    assert "2 columns for 3 variables" in data.check_variables(["A", "B", "C"])
