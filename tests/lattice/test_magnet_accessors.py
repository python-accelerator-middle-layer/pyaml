import at
import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.lattice.abstract_impl import RWHardwareArray, RWHardwareScalar, RWStrengthArray, RWStrengthScalar
from pyaml.magnet.hcorrector import HCorrector
from pyaml.magnet.identity_cfm_model import IdentityCFMagnetModel
from pyaml.magnet.identity_model import IdentityMagnetModel
from pyaml.magnet.vcorrector import VCorrector


@pytest.mark.parametrize("accessor_type", [RWStrengthScalar, RWHardwareScalar])
def test_setting_zero_length_scalar_magnet_raises(accessor_type):
    element = at.Corrector("COR", 0.0, [0.0, 0.0], PolynomA=[0.0], PolynomB=[0.0])
    model = IdentityMagnetModel(physics="COR", unit="rad")
    accessor = accessor_type([element], HCorrector.polynom, model)

    with pytest.raises(PyAMLException, match="length must be non-zero"):
        accessor.set(1.0e-6)

    assert accessor.get() == 0.0
    assert np.isfinite(element.PolynomB[0])


@pytest.mark.parametrize("accessor_type", [RWStrengthArray, RWHardwareArray])
def test_setting_zero_length_combined_function_magnet_raises(accessor_type):
    element = at.Corrector("COR", 0.0, [0.0, 0.0], PolynomA=[0.0], PolynomB=[0.0])
    model = IdentityCFMagnetModel(
        multipoles=["B0", "A0"],
        physics=["HCOR", "VCOR"],
        units=["rad", "rad"],
    )
    accessor = accessor_type([element], [HCorrector.polynom, VCorrector.polynom], model)

    with pytest.raises(PyAMLException, match="length must be non-zero"):
        accessor.set(np.array([1.0e-6, -2.0e-6]))

    np.testing.assert_allclose(accessor.get(), np.zeros(2))
    assert np.all(np.isfinite(element.PolynomA))
    assert np.all(np.isfinite(element.PolynomB))
