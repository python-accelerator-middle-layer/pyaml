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


def _ring(corrector):
    qf = at.Quadrupole("QF", 0.5, 1.2)
    qd = at.Quadrupole("QD", 0.5, -1.2)
    cell = [qf, at.Drift("D1", 1.0), at.Monitor("BPM"), qd, at.Drift("D2", 1.0)]
    return at.Lattice([corrector] + cell * 8, energy=2e9, periodicity=1)


def _orbit(corrector):
    """Closed orbit (x, y) at the monitors of a small ring holding ``corrector``."""
    orbit = at.find_orbit4(_ring(corrector), refpts=at.Monitor)[1]
    return orbit[:, [0, 2]]


@pytest.mark.parametrize("length", [0.0, 0.2])
@pytest.mark.parametrize(
    "polynom, kick_angle",
    [(HCorrector.polynom, [1.0e-4, 0.0]), (VCorrector.polynom, [0.0, 1.0e-4])],
)
def test_corrector_pass_strength_moves_the_orbit(length, polynom, kick_angle):
    # CorrectorPass integrates KickAngle and ignores the polynoms: the strength has to reach KickAngle
    reference = _orbit(at.Corrector("REF", length, kick_angle))
    assert np.abs(reference).max() > 1.0e-5

    element = at.Corrector("COR", length, [0.0, 0.0], PolynomA=[0.0], PolynomB=[0.0])
    accessor = RWStrengthScalar([element], polynom, IdentityMagnetModel(physics="COR", unit="rad"))
    accessor.set(1.0e-4)

    assert accessor.get() == pytest.approx(1.0e-4)
    np.testing.assert_allclose(element.KickAngle, kick_angle)
    np.testing.assert_allclose(_orbit(element), reference, rtol=0, atol=1.0e-12)


def test_corrector_pass_without_polynoms_is_supported():
    element = at.Corrector("COR", 0.0, [0.0, 0.0])
    accessor = RWStrengthScalar([element], HCorrector.polynom, IdentityMagnetModel(physics="COR", unit="rad"))

    accessor.set(1.0e-4)

    assert accessor.get() == pytest.approx(1.0e-4)
    np.testing.assert_allclose(element.KickAngle, [1.0e-4, 0.0])


def test_corrector_pass_reads_the_kick_of_the_lattice():
    element = at.Corrector("COR", 0.2, [2.0e-5, -3.0e-5])
    model = IdentityMagnetModel(physics="COR", unit="rad")

    assert RWStrengthScalar([element], HCorrector.polynom, model).get() == pytest.approx(2.0e-5)
    assert RWStrengthScalar([element], VCorrector.polynom, model).get() == pytest.approx(-3.0e-5)


@pytest.mark.parametrize("accessor_type", [RWStrengthArray, RWHardwareArray])
def test_corrector_pass_combined_function_strengths_move_the_orbit(accessor_type):
    reference = _orbit(at.Corrector("REF", 0.0, [1.0e-4, -2.0e-4]))
    element = at.Corrector("COR", 0.0, [0.0, 0.0], PolynomA=[0.0], PolynomB=[0.0])
    model = IdentityCFMagnetModel(multipoles=["B0", "A0"], physics=["HCOR", "VCOR"], units=["rad", "rad"])
    accessor = accessor_type([element], [HCorrector.polynom, VCorrector.polynom], model)

    accessor.set(np.array([1.0e-4, -2.0e-4]))

    np.testing.assert_allclose(accessor.get(), [1.0e-4, -2.0e-4])
    np.testing.assert_allclose(_orbit(element), reference, rtol=0, atol=1.0e-12)


def test_split_corrector_pass_shares_the_kick_by_length():
    elements = [at.Corrector("COR_A", 0.1, [0.0, 0.0]), at.Corrector("COR_B", 0.3, [0.0, 0.0])]
    accessor = RWStrengthScalar(elements, HCorrector.polynom, IdentityMagnetModel(physics="COR", unit="rad"))

    accessor.set(1.0e-4)

    assert elements[0].KickAngle[0] == pytest.approx(0.25e-4)
    assert elements[1].KickAngle[0] == pytest.approx(0.75e-4)
    assert accessor.get() == pytest.approx(1.0e-4)


def test_multipole_corrector_agrees_with_corrector_pass():
    # Same strength, same orbit, whichever pass method the lattice uses for its correctors
    model = IdentityMagnetModel(physics="COR", unit="rad")
    thin = at.ThinMultipole("COR", [0.0], [0.0])
    kicker = at.Corrector("COR", 0.0, [0.0, 0.0])
    for element in (thin, kicker):
        RWStrengthScalar([element], HCorrector.polynom, model).set(1.0e-4)

    np.testing.assert_allclose(_orbit(thin), _orbit(kicker), rtol=0, atol=1.0e-12)


@pytest.mark.parametrize(
    "element",
    [
        at.ThinMultipole("COR", [0.0], [0.0], KickAngle=[1.0e-4, 0.0]),
        at.Multipole("COR", 0.2, [0.0], [0.0], KickAngle=[1.0e-4, 0.0]),
        at.Dipole("COR", 0.2, 0.0, KickAngle=[1.0e-4, 0.0]),
    ],
    ids=["thin multipole", "multipole", "dipole"],
)
def test_multipole_kick_angle_is_part_of_the_strength(element):
    # The multipole pass methods add KickAngle to the polynom: the strength is the sum, and a write replaces it
    element = element.deepcopy()
    kicked = _orbit(element)
    assert np.abs(kicked).max() > 1.0e-5
    accessor = RWStrengthScalar([element], HCorrector.polynom, IdentityMagnetModel(physics="COR", unit="rad"))

    assert accessor.get() == pytest.approx(1.0e-4)

    accessor.set(1.0e-4)
    assert accessor.get() == pytest.approx(1.0e-4)
    # a thick integrator does not treat the two attributes identically to the last digit
    np.testing.assert_allclose(_orbit(element), kicked, rtol=1.0e-6, atol=0)

    accessor.set(0.0)
    np.testing.assert_allclose(_orbit(element), 0.0, atol=1.0e-12)


def test_kick_angle_ignored_by_the_pass_method_is_not_read():
    element = at.Quadrupole("QUAD", 0.2, 1.0, PassMethod="QuadLinearPass", KickAngle=[1.0e-4, 0.0])
    accessor = RWStrengthScalar([element], HCorrector.polynom, IdentityMagnetModel(physics="COR", unit="rad"))

    assert accessor.get() == 0.0
