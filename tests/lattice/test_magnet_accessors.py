import at
import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.lattice.abstract_impl import (
    RWHardwareArray,
    RWHardwareScalar,
    RWSerializedStrength,
    RWStrengthArray,
    RWStrengthScalar,
)
from pyaml.magnet.hcorrector import HCorrector
from pyaml.magnet.identity_cfm_model import IdentityCFMagnetModel
from pyaml.magnet.identity_model import IdentityMagnetModel
from pyaml.magnet.vcorrector import VCorrector


def _thin_corrector(name="COR"):
    return at.Corrector(name, 0.0, [0.0, 0.0], PolynomA=[0.0], PolynomB=[0.0])


@pytest.mark.parametrize("accessor_type", [RWStrengthScalar, RWHardwareScalar])
def test_zero_length_scalar_magnet_stores_integrated_strength(accessor_type):
    element = _thin_corrector()
    model = IdentityMagnetModel(physics="COR", unit="rad")
    accessor = accessor_type([element], HCorrector.polynom, model)

    accessor.set(1.0e-6)

    # AT convention: a thin element stores the integrated strength in its polynom
    assert element.PolynomB[0] == pytest.approx(-1.0e-6)
    assert accessor.get() == pytest.approx(1.0e-6)


@pytest.mark.parametrize("accessor_type", [RWStrengthScalar, RWHardwareScalar])
def test_zero_length_split_magnet_shares_integrated_strength_equally(accessor_type):
    elements = [_thin_corrector("COR_A"), _thin_corrector("COR_B")]
    model = IdentityMagnetModel(physics="COR", unit="rad")
    accessor = accessor_type(elements, HCorrector.polynom, model)

    accessor.set(1.0e-6)

    assert elements[0].PolynomB[0] == pytest.approx(-0.5e-6)
    assert elements[1].PolynomB[0] == pytest.approx(-0.5e-6)
    assert accessor.get() == pytest.approx(1.0e-6)


@pytest.mark.parametrize("accessor_type", [RWStrengthScalar, RWHardwareScalar])
def test_thick_scalar_magnet_is_unchanged(accessor_type):
    element = at.Corrector("COR", 0.2, [0.0, 0.0], PolynomA=[0.0], PolynomB=[0.0])
    model = IdentityMagnetModel(physics="COR", unit="rad")
    accessor = accessor_type([element], HCorrector.polynom, model)

    accessor.set(1.0e-6)

    assert element.PolynomB[0] == pytest.approx(-5.0e-6)
    assert accessor.get() == pytest.approx(1.0e-6)


@pytest.mark.parametrize("accessor_type", [RWStrengthArray, RWHardwareArray])
def test_zero_length_combined_function_magnet_stores_integrated_strengths(accessor_type):
    element = _thin_corrector()
    model = IdentityCFMagnetModel(
        multipoles=["B0", "A0"],
        physics=["HCOR", "VCOR"],
        units=["rad", "rad"],
    )
    accessor = accessor_type([element], [HCorrector.polynom, VCorrector.polynom], model)

    accessor.set(np.array([1.0e-6, -2.0e-6]))

    assert element.PolynomB[0] == pytest.approx(-1.0e-6)
    assert element.PolynomA[0] == pytest.approx(-2.0e-6)
    np.testing.assert_allclose(accessor.get(), [1.0e-6, -2.0e-6])


def test_zero_length_serialized_magnets_share_strength_equally():
    elements = [_thin_corrector("COR_A"), _thin_corrector("COR_B")]
    model = IdentityMagnetModel(physics="COR", unit="rad")
    strengths = [RWStrengthScalar([e], HCorrector.polynom, model) for e in elements]
    currents = [RWHardwareScalar([e], HCorrector.polynom, model) for e in elements]
    serialized = [RWSerializedStrength(strengths, currents, i) for i in range(len(elements))]

    serialized[0].set(1.0e-6)

    assert serialized[0].get() == pytest.approx(0.5e-6)
    assert serialized[1].get() == pytest.approx(0.5e-6)
    assert elements[0].PolynomB[0] == pytest.approx(-0.5e-6)
    assert elements[1].PolynomB[0] == pytest.approx(-0.5e-6)


def test_serialized_magnets_mixing_thin_and_thick_is_rejected():
    elements = [_thin_corrector("COR_A"), at.Corrector("COR_B", 0.2, [0.0, 0.0], PolynomA=[0.0], PolynomB=[0.0])]
    model = IdentityMagnetModel(physics="COR", unit="rad")
    strengths = [RWStrengthScalar([e], HCorrector.polynom, model) for e in elements]
    currents = [RWHardwareScalar([e], HCorrector.polynom, model) for e in elements]

    with pytest.raises(PyAMLException, match="all thin .* or all thick"):
        RWSerializedStrength(strengths, currents, 0)
