from unittest.mock import Mock

import at
import numpy as np
import pytest

from pyaml.lattice.abstract_impl import RWHardwareTrim, RWStrengthScalar, RWStrengthTrim, RWStrengthTuple
from pyaml.magnet.hcorrector import HCorrector
from pyaml.magnet.identity_model import IdentityMagnetModel


def test_strength_trim_preserves_main_and_updates_lattice():
    element = at.Dipole("BEND", 0.4, 0.02)
    model = IdentityMagnetModel(physics="COR", unit="rad")
    total = RWStrengthScalar([element], HCorrector.polynom, model)
    strengths = RWStrengthTuple(total, initial=(0.03, 0.005))
    trim = RWStrengthTrim(strengths)

    assert trim.get() == 0.005
    trim.set(-0.002)
    assert strengths.get() == (0.03, -0.002)
    assert total.get() == pytest.approx(0.028)
    assert element.PolynomB[0] == pytest.approx(-0.02)
    assert element.BendingAngle == 0.02
    assert trim.unit() == "rad"


def test_hardware_trim_uses_nonlinear_model_and_signed_scaling():
    model = Mock()
    model.compute_strengths.side_effect = lambda currents: np.asarray(currents) ** 3 + 7.0
    model.compute_hardware_values.side_effect = lambda strengths: np.cbrt(np.asarray(strengths) - 7.0)
    model.get_hardware_units.return_value = ["A"]
    total = Mock()
    strengths = RWStrengthTuple(total, initial=(15.0, 19.0))  # f(2), f(3) - f(2)
    trim_strength = RWStrengthTrim(strengths)
    hardware = RWHardwareTrim(strengths, model, trim_factor=-2.0)

    assert hardware.get() == pytest.approx(-0.5)
    total.set.reset_mock()
    hardware.set(0.5)  # Effective current 2 - 2 * 0.5 = 1.
    assert strengths.get() == pytest.approx((15.0, -7.0))
    total.set.assert_called_once_with(pytest.approx(8.0))
    assert hardware.get() == pytest.approx(0.5)

    trim_strength.set(19.0)
    assert hardware.get() == pytest.approx(-0.5)
    assert hardware.unit() == "A"
    assert hardware.get_model() is model

    # Family integration can preserve physical trim current at a new operating point.
    current = hardware.get()
    strengths.set((34.0, trim_strength.get()))  # Main current is now 3.
    hardware.set(current)
    assert strengths.get() == pytest.approx((34.0, 37.0))  # f(4) - f(3)
    assert hardware.get() == pytest.approx(current)


def test_failed_hardware_conversion_preserves_strengths():
    total = Mock()
    strengths = RWStrengthTuple(total, initial=(1.0, 0.2))
    total.set.reset_mock()
    model = Mock()
    model.compute_hardware_values.side_effect = ValueError("conversion failed")
    hardware = RWHardwareTrim(strengths, model)

    with pytest.raises(ValueError, match="conversion failed"):
        hardware.set(0.5)
    assert strengths.get() == (1.0, 0.2)
    total.set.assert_not_called()
