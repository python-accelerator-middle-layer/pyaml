"""Simulator attachment and main/trim writes, without control-system dependencies."""

import at
import numpy as np
import pytest

from pyaml.lattice.abstract_impl import RWStrengthScalar
from pyaml.lattice.simulator import Simulator
from pyaml.magnet.inline_curve import InlineCurve
from pyaml.magnet.linear_serialized_with_trims_model import LinearSerializedMagnetWithTrimsModel
from pyaml.magnet.serialized_magnet_trims import SerializedMagnetsWithTrims
from pyaml.magnet.trim_coil import TrimCoil


def test_serialized_trim_simulator_attachment(tmp_path):
    path = tmp_path / "ring.mat"
    at.save_lattice(at.Lattice([at.Dipole(name, 1, 0.01) for name in ["D1", "D2"]], energy=6e9), path)
    simulator = Simulator("design", str(path))
    model = LinearSerializedMagnetWithTrimsModel(
        curves=InlineCurve([[0, 0], [1, 1], [2, 4], [3, 9]]),
        trims=[TrimCoil("D2", "T2", "trim/current", trim_factor=-2, hardware_unit="trim A")],
        powerconverter="main/current",
        unit="rad",
        hardware_unit="A",
    )
    family = SerializedMagnetsWithTrims("series", "B0", ["D1", "D2"], model)
    model.set_magnet_rigidity(1.0)
    simulator.fill_device([family])
    attached = simulator.serialized_magnet["series"]
    trim = simulator.magnet["T2"]
    assert isinstance(attached, SerializedMagnetsWithTrims)
    assert attached.get_trim_magnets() == [trim]
    assert attached.names() == ["D1", "D2"]
    assert len(attached) == 2
    assert trim.peer is simulator
    assert simulator.get_at_elems(trim) == simulator.get_at_elems(attached[1])
    assert trim.hardware.unit() == "trim A"
    np.testing.assert_allclose(attached.strengths.get(), [0.01, 0.01])
    assert trim.strength.get() == 0
    attached.hardware.set(1.0)
    trim.hardware.set(-0.25)
    assert trim.strength.get() == pytest.approx(1.5)
    # Main-strength writes currently preserve trim current, not trim strength.
    attached.strength.set(model.compute_mean_strength(2.0))
    assert trim.hardware.get() == pytest.approx(-0.25)
    assert trim.strength.get() == pytest.approx(2.5)
    trim.strength.set(1.0)
    assert attached.hardware.get() == pytest.approx(2.0)
    assert trim.hardware.get() == pytest.approx(-0.1)
    attached.strengths.set(model.compute_strengths([1.0]))
    assert trim.hardware.get() == pytest.approx(-0.1)
    attached[1].strength.set(model.compute_strengths([2.0])[1])
    assert trim.hardware.get() == pytest.approx(-0.1)
    attached.hardwares.set(np.array([1.0, 1.0]))
    assert trim.hardware.get() == pytest.approx(-0.1)
    for index, member in enumerate(attached):
        total = RWStrengthScalar(simulator.get_at_elems(member), member.polynom, model.get_sub_model(index))
        expected = member.strength.get() + (trim.strength.get() if index == 1 else 0)
        assert total.get() == pytest.approx(expected)
