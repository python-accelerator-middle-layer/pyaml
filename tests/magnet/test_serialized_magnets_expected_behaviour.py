"""
Expected behaviour of a series of magnets, written as a basis for discussion.

What is a series?
    N magnets wired on ONE power supply. There is a single current I for all of them.
    Magnet i has its own excitation curve f_i: its strength is k_i = f_i(I).

What happens when we ask for strengths?
    We ask for one strength k_i per magnet. The power supply can only take one current, so the
    code looks for the current I that best matches all the requested strengths:

        sum over i of (f_i(I) - k_i) / span_i == 0

    span_i is the strength range of the curve of magnet i, f_i(I_max) - f_i(I_min), with its sign.
    Dividing by span_i makes every term dimensionless and increasing with I, so:
      - every magnet weighs the same, whatever its unit (a sextupole does not outweigh a quadrupole),
      - a magnet wired in reverse (negative calibration) is handled like the others,
      - the equation always has a solution.

    A request is "consistent" when one single current gives all the requested strengths: the code
    must then find this current exactly. Otherwise the request is "inconsistent": the code returns a
    compromise and logs a warning.

How to read and modify these tests?
    Each test builds a small series with simple curves (current in A, strength = curve value x
    calibration), asks for strengths, and checks the current. To discuss another expected behaviour,
    change the curves, the calibrations, the request or the expected current in the test.
"""

import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.magnet.inline_curve import InlineCurve
from pyaml.magnet.linear_serialized_model import LinearSerializedMagnetModel

# Excitation curves: each row is [current (A), strength].
# Straight line, 1.0 at 100 A.
LINEAR = np.array([[0.0, 0.0], [100.0, 1.0]])
# Steep up to 50 A, then flatter: the magnet starts to saturate.
SATURATING = np.array([[0.0, 0.0], [50.0, 0.6], [100.0, 0.8]])
# Straight line up to 110 A, used for the quadrupole and the sextupole example.
QUAD_SEXTU = np.array([[0.0, 0.0], [110.0, 1.1]])
# Fully saturated above 80 A: the strength stays at 0.8 from 80 A to 110 A.
PLATEAU = np.array([[0.0, 0.0], [80.0, 0.8], [110.0, 0.8]])
# Two slopes: steep up to 50 A, flatter after.
TWO_SLOPES = np.array([[0.0, 0.0], [50.0, 1.0], [100.0, 1.5]])


def make_series(curves: list[np.ndarray], calibrations: list[float]) -> LinearSerializedMagnetModel:
    """Build the model of a series: one curve and one calibration factor per magnet."""
    series = LinearSerializedMagnetModel(
        curves=[InlineCurve(mat=curve) for curve in curves],
        calibration_factors=calibrations,
        calibration_offsets=0.0,
        unit="m-1",
        hardware_unit="A",
        powerconverter="the/power/supply",
    )
    series.set_number_of_magnets(len(curves))
    # Magnetic rigidity of 1: the strength is directly curve value x calibration
    series.set_magnet_rigidity(1.0)
    return series


def relative_errors(series: LinearSerializedMagnetModel, current: float, requested: list[float]) -> list[str]:
    """Return, for each magnet, how far the strength obtained at `current` is from the requested one."""
    obtained = series.compute_strengths([current])
    return [f"{100 * (got - wanted) / wanted:+.1f} %" for got, wanted in zip(obtained, requested, strict=True)]


# ---------------------------------------------------------------------------------------------------------------------
# Magnets wired in reverse (opposite polarities)
# ---------------------------------------------------------------------------------------------------------------------


def test_opposite_polarities_with_different_saturations_reach_a_consistent_request():
    # Step 1: a series of two magnets on ONE power supply.
    #   - magnet 0 follows the LINEAR curve, calibration +1
    #   - magnet 1 follows the SATURATING curve, calibration -1: it is wired in reverse,
    #     its strength goes down when the current goes up
    series = make_series([LINEAR, SATURATING], calibrations=[1.0, -1.0])

    # Step 2: ask for the strengths the two magnets really have at 40 A.
    #   This request is "consistent": one single current (40 A) gives both strengths.
    requested = series.compute_strengths([40.0])

    # Step 3: the power-supply current computed from these strengths.
    current = series.compute_hardware_from_strengths(requested)

    # Expected: we find 40 A back, even though the two magnets have opposite polarities.
    assert current == pytest.approx(40.0)


def test_opposite_polarities_with_identical_curves_reach_a_consistent_request():
    # Step 1: two magnets on ONE power supply, same LINEAR curve, the second one wired in reverse.
    #   At any current, their strengths are exactly opposite: k_1 = -k_0.
    series = make_series([LINEAR, LINEAR], calibrations=[1.0, -1.0])

    # Step 2: ask for the strengths they have at 40 A: +0.4 and -0.4.
    requested = series.compute_strengths([40.0])

    # Step 3: the power-supply current computed from these strengths.
    current = series.compute_hardware_from_strengths(requested)

    # Expected: 40 A. The two strengths add up to 0, but this must not give 0 A.
    assert current == pytest.approx(40.0)


def test_family_strength_of_opposite_polarities_uses_the_polarity_of_the_first_magnet():
    # Step 1: the same two magnets, the second one wired in reverse.
    series = make_series([LINEAR, LINEAR], calibrations=[1.0, -1.0])

    # Step 2: read the family strength at 40 A.
    #   The raw strengths are +0.4 and -0.4. The family strength takes each strength with the
    #   polarity of the first magnet, so the reversed magnet counts as +0.4, not -0.4.
    family_strength = series.compute_mean_strength(40.0)

    # Expected: 0.4 (and not 0.0, the plain average of +0.4 and -0.4).
    assert family_strength == pytest.approx(0.4)

    # Step 3: set this family strength back.
    # Expected: 40 A.
    assert series.compute_hardware_from_mean_strength(0.4) == pytest.approx(40.0)


def test_family_strength_of_opposite_polarities_with_different_saturations():
    # Step 1: LINEAR magnet, plus a SATURATING magnet wired in reverse.
    series = make_series([LINEAR, SATURATING], calibrations=[1.0, -1.0])

    # Step 2: at 40 A, the strengths are +0.40 and -0.48.
    #   With the polarity of the first magnet, the family strength is (0.40 + 0.48) / 2 = 0.44.
    assert series.compute_mean_strength(40.0) == pytest.approx(0.44)

    # Step 3: set this family strength back.
    # Expected: 40 A.
    assert series.compute_hardware_from_mean_strength(0.44) == pytest.approx(40.0)


# ---------------------------------------------------------------------------------------------------------------------
# Magnets of different natures on one power supply (strengths with very different magnitudes)
# ---------------------------------------------------------------------------------------------------------------------


def test_quadrupole_and_sextupole_share_the_error_when_the_sextupole_asks_for_more():
    # Step 1: a "quadrupole" (calibration 1) and a "sextupole" (calibration 60) on the same curve.
    #   The sextupole strengths are 60 times bigger numbers than the quadrupole strengths.
    series = make_series([QUAD_SEXTU, QUAD_SEXTU], calibrations=[1.0, 60.0])

    # Step 2: an inconsistent request.
    #   - the quadrupole alone would need 50 A (0.5)
    #   - the sextupole alone would need 60 A (36 = 60 x 0.6)
    #   No single current gives both: the result is a compromise.
    requested = [0.5, 36.0]

    # Step 3: the power-supply current computed from these strengths.
    current = series.compute_hardware_from_strengths(np.array(requested))

    # Expected: 55 A, halfway. Both magnets miss their target by about the same amount, the bigger
    # numbers of the sextupole do not make it win.
    assert current == pytest.approx(55.0), f"relative errors: {relative_errors(series, current, requested)}"


def test_quadrupole_and_sextupole_share_the_error_when_the_quadrupole_asks_for_more():
    # Step 1: the same quadrupole (calibration 1) and sextupole (calibration 60).
    series = make_series([QUAD_SEXTU, QUAD_SEXTU], calibrations=[1.0, 60.0])

    # Step 2: an inconsistent request, the other way round.
    #   - the quadrupole alone would need 60 A (0.6)
    #   - the sextupole alone would need 50 A (30 = 60 x 0.5)
    requested = [0.6, 30.0]

    # Step 3: the power-supply current computed from these strengths.
    current = series.compute_hardware_from_strengths(np.array(requested))

    # Expected: 55 A, halfway again.
    assert current == pytest.approx(55.0), f"relative errors: {relative_errors(series, current, requested)}"


# ---------------------------------------------------------------------------------------------------------------------
# Particular situations
# ---------------------------------------------------------------------------------------------------------------------


def test_two_saturated_magnets_give_the_middle_of_the_plateau():
    # Step 1: two magnets with the PLATEAU curve: from 80 A to 110 A the strength stays at 0.8.
    series = make_series([PLATEAU, PLATEAU], calibrations=[1.0, 1.0])

    # Step 2: ask for 0.8 on both magnets. Every current between 80 A and 110 A gives it.
    current = series.compute_hardware_from_strengths(np.array([0.8, 0.8]))

    # Expected: the middle of the interval, 95 A, rather than one of its ends.
    assert current == pytest.approx(95.0)


def test_strengths_outside_the_curves_are_clamped_with_a_warning(caplog):
    # Step 1: two magnets with the LINEAR curve: the strongest they can be is 1.0, at 100 A.
    series = make_series([LINEAR, LINEAR], calibrations=[1.0, 1.0])

    # Step 2: ask for 5.0, far more than the curves can give.
    with caplog.at_level("WARNING"):
        current = series.compute_hardware_from_strengths(np.array([5.0, 5.0]))

    # Expected: the current stops at the end of the curves (100 A), and a warning says so.
    assert current == pytest.approx(100.0)
    assert "outside the range reachable by the excitation curves" in caplog.text


def test_a_curve_with_no_strength_range_cannot_give_a_current():
    # Step 1: magnet 1 has a flat curve: its strength is 0.3 whatever the current.
    flat = np.array([[0.0, 0.3], [100.0, 0.3]])
    series = make_series([LINEAR, flat], calibrations=[1.0, 1.0])

    # Step 2: ask for strengths. The flat magnet says nothing about the current.
    # Expected: an error, rather than a current computed from a meaningless strength.
    with pytest.raises(PyAMLException, match="no strength range"):
        series.compute_hardware_from_strengths(np.array([0.4, 0.3]))


def test_the_model_has_a_single_rule_to_turn_strengths_into_a_current():
    # Step 1: two magnets with the TWO_SLOPES curve, calibrations 1.0 and 1.2.
    series = make_series([TWO_SLOPES, TWO_SLOPES], calibrations=[1.0, 1.2])

    # Step 2: the same request through the two methods of the model that turn strengths into a current.
    requested = [0.8, 1.6]
    from_hardware_values = series.compute_hardware_values(requested)[0]
    from_strengths = series.compute_hardware_from_strengths(requested)

    # Expected: the same current.
    assert from_hardware_values == pytest.approx(from_strengths)


# ---------------------------------------------------------------------------------------------------------------------
# One hardware value per magnet, on a real series
# ---------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "wrong_value",
    [
        pytest.param([10.0, 20.0], id="2 values for 31 magnets"),
        pytest.param(7.0, id="a single number"),
        pytest.param([80.0] * 34, id="34 values for 31 magnets"),
    ],
)
def test_family_hardwares_need_one_value_per_magnet(wrong_value):
    # Step 1: the QF1A series of the test lattice: 31 magnets on one power supply.
    sr = Accelerator.load("tests/config/sr_serialized_magnets.yaml", include_locations=False, ignore_external=True)
    family = sr.design.serialized_magnet.get("QF1A")
    family.hardware.set(80.0)

    # Step 2: write a list of hardware values that does not have one value per magnet.
    # Expected: an error, and the power supply is not moved.
    with pytest.raises(PyAMLException, match="One hardware value per magnet"):
        family.hardwares.set(wrong_value)
    assert family.hardware.get() == pytest.approx(80.0)

    # Step 3: with one value per magnet it works (a single value is written with family.hardware).
    family.hardwares.set([75.0] * family.get_nb_magnets())
    assert family.hardware.get() == pytest.approx(75.0)
