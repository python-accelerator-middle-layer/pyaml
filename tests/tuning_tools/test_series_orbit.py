"""
Orbit tools with a series of correctors.

The correctors of a series share ONE power supply: the series is one knob, its serialized family. The orbit response
matrix has one input for the family, and the orbit correction writes the power supply of the series once.

Configuration (tests/config/sr_series_orbit.yaml):
    SH1A_SERIES: one power supply for the horizontal correctors of SH1A-C05..C08,
    SH1A-C09, SH1A-C10: individually powered horizontal correctors,
    SH3E-C05..C08: individually powered vertical correctors.
"""

import numpy as np
import pytest

from pyaml.accelerator import Accelerator

CONFIG = "tests/config/sr_series_orbit.yaml"
HKNOBS = ["SH1A_SERIES", "SH1A-C09", "SH1A-C10"]
VKNOBS = ["SH3E-C05", "SH3E-C06", "SH3E-C07", "SH3E-C08"]


def measure_and_load(tmp_path):
    """Measure the orbit response matrix, load it in the orbit tool and return the simulator."""
    sr = Accelerator.load(CONFIG)
    design = sr.design
    orm = design.tool.get("ORM")
    assert orm.measure()
    path = tmp_path / "orm.json"
    orm.save(path)
    design.tool.get("ORBIT").load(path)
    return design


def test_orbit_response_matrix_has_one_input_for_a_series(tmp_path):
    design = measure_and_load(tmp_path)
    measurement = design.tool.get("ORM").latest_measurement

    # The series is one input, named after its family, with its plane
    assert measurement["variable_names"] == HKNOBS + VKNOBS
    assert measurement["variable_planes"] == ["H"] * 3 + ["V"] * 4
    assert np.shape(measurement["matrix"]) == (2 * 20, 7)


def test_orbit_correction_writes_the_power_supply_of_a_series_once(tmp_path, monkeypatch):
    design = measure_and_load(tmp_path)
    orbit = design.tool.get("ORBIT")
    family = design.serialized_magnet.get("SH1A_SERIES")
    bpms = design.diagnostic.bpms.get("BPM")

    # Distort the horizontal orbit with a corrector that is not in the arrays
    design.get_lattice().get_elements("SH1A-C04")[0].PolynomB[0] = 2e-5
    distorted = np.std(bpms.positions.get()[:, 0])

    # Record the writes to the family and to the magnets of the series
    family_writes = []
    family_strength = family.strength
    original_family_set = type(family_strength).set

    def spy_family(self, value):
        if self is family_strength:
            family_writes.append(value)
        original_family_set(self, value)

    monkeypatch.setattr(type(family_strength), "set", spy_family)

    member_writes = []
    member_strength_class = type(family[0].strength)
    original_member_set = member_strength_class.set

    def spy_member(self, value):
        if any(self is m.strength for m in family):
            member_writes.append(value)
        original_member_set(self, value)

    monkeypatch.setattr(member_strength_class, "set", spy_member)

    orbit.correct(plane="H")

    # The series is written once, through its family, and the orbit is corrected
    assert len(family_writes) == 1
    assert member_writes == []
    assert family.strength.get() != 0.0
    assert np.std(bpms.positions.get()[:, 0]) < 0.5 * distorted


def test_pysc_interface_resolves_a_family_name():
    from pyaml.external.pySC_interface import pySCInterface

    sr = Accelerator.load(CONFIG)
    design = sr.design
    family = design.serialized_magnet.get("SH1A_SERIES")
    interface = pySCInterface(element_holder=design, bpm_array_name="BPM")
    interface.set_wait_time = 0

    # A family name gives the average strength of the series and writes its power supply
    interface.set("SH1A_SERIES", 1e-5)

    assert interface.get("SH1A_SERIES") == family.strength.get()
    assert family.strength.get() == pytest.approx(1e-5)
    # A magnet name still gives that magnet
    assert interface.get("SH1A-C09") == design.magnet.get("SH1A-C09").strength.get()
