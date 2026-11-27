"""
Expected behaviour of a series of magnets, written as a basis for discussion.

What is a series?
    N magnets wired on ONE power supply. There is a single current I for all of them.
    Magnet i has its own excitation curve f_i: its strength is k_i = f_i(I).

What happens when we ask for strengths?
    We ask for one strength k_i per magnet. The power supply can only take one current, so the
    code looks for the current I that best matches all the requested strengths:

        sum over i of (f_i(I) - k_i) / span_i == 0

    [I_min, I_max] is the current range shared by all the curves of the series: the power supply
    drives every magnet, so this is the only range that matters. span_i is the strength range of
    magnet i on it, f_i(I_max) - f_i(I_min), with its sign. Dividing by span_i makes every term
    dimensionless and increasing with I, so:
      - every magnet weighs the same, whatever its unit (a sextupole does not outweigh a quadrupole),
      - a magnet wired in reverse (negative calibration) is handled like the others,
      - extending the table of a curve does not change the result,
      - the equation always has a solution.

    A request is "consistent" when one single current gives all the requested strengths: the code
    must then find this current exactly. Otherwise the request is "inconsistent": the code returns a
    compromise and logs a warning. When several currents give the requested strengths (a plateau),
    the present current is kept if it is one of them.

What is the family strength?
    The average of the strengths, each one taken with the polarity p_i (+1 or -1) declared for its
    magnet: sum over i of p_i * f_i(I) / N. A magnet wired in reverse must be declared with -1, so
    that it counts with its magnitude instead of cancelling the others.

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


def make_series(
    curves: list[np.ndarray], calibrations: list[float], polarities: list[int] | None = None
) -> LinearSerializedMagnetModel:
    """Build the model of a series: one curve, one calibration factor and one polarity (default +1) per magnet."""
    series = LinearSerializedMagnetModel(
        curves=[InlineCurve(mat=curve) for curve in curves],
        calibration_factors=calibrations,
        polarities=polarities,
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
    #     its strength goes down when the current goes up, so it is declared with polarity -1
    series = make_series([LINEAR, SATURATING], calibrations=[1.0, -1.0], polarities=[1, -1])

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
    series = make_series([LINEAR, LINEAR], calibrations=[1.0, -1.0], polarities=[1, -1])

    # Step 2: ask for the strengths they have at 40 A: +0.4 and -0.4.
    requested = series.compute_strengths([40.0])

    # Step 3: the power-supply current computed from these strengths.
    current = series.compute_hardware_from_strengths(requested)

    # Expected: 40 A. The two strengths add up to 0, but this must not give 0 A.
    assert current == pytest.approx(40.0)


def test_family_strength_of_opposite_polarities_uses_the_declared_polarities():
    # Step 1: the same two magnets, the second one wired in reverse and declared with polarity -1.
    series = make_series([LINEAR, LINEAR], calibrations=[1.0, -1.0], polarities=[1, -1])

    # Step 2: read the family strength at 40 A.
    #   The raw strengths are +0.4 and -0.4. The family strength takes each strength with the
    #   declared polarity of its magnet, so the reversed magnet counts as +0.4, not -0.4.
    family_strength = series.compute_mean_strength(40.0)

    # Expected: 0.4 (and not 0.0, the plain average of +0.4 and -0.4).
    assert family_strength == pytest.approx(0.4)

    # Step 3: set this family strength back.
    # Expected: 40 A.
    assert series.compute_hardware_from_mean_strength(0.4) == pytest.approx(40.0)


def test_family_strength_of_opposite_polarities_with_different_saturations():
    # Step 1: LINEAR magnet, plus a SATURATING magnet wired in reverse (polarity -1).
    series = make_series([LINEAR, SATURATING], calibrations=[1.0, -1.0], polarities=[1, -1])

    # Step 2: at 40 A, the strengths are +0.40 and -0.48.
    #   With the declared polarities, the family strength is (0.40 + 0.48) / 2 = 0.44.
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


# ---------------------------------------------------------------------------------------------------------------------
# Edge cases of the normalized residual: curve tables of different lengths, plateaus, polarities
# ---------------------------------------------------------------------------------------------------------------------

# The LINEAR curve tabulated up to 200 A instead of 100 A: same magnet, same slope, longer table.
LINEAR_UP_TO_200 = np.array([[0.0, 0.0], [200.0, 2.0]])
# The LINEAR curve with one more point at 300 A, on the same straight line: nothing changes below 100 A.
LINEAR_EXTENDED = np.array([[0.0, 0.0], [100.0, 1.0], [300.0, 3.0]])

TANGO_DUMMY = [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}]


def plateau_series_fragment(calibrations: list[float]) -> dict:
    """Return a configuration fragment adding a series of two PLATEAU magnets, and an array holding them."""
    return {
        "arrays": [{"type": "pyaml.arrays.magnet", "name": "PLATEAU_MAGNETS", "elements": ["QF4A-C10", "QF4B-C10"]}],
        "devices": [
            {
                "type": "pyaml.magnet.serialized_magnet",
                "name": "plateauSeries",
                "function": "B1",
                "elements": ["QF4A-C10", "QF4B-C10"],
                "model": {
                    "type": "pyaml.magnet.linear_serialized_model",
                    "calibration_factors": calibrations,
                    "calibration_offsets": 0.0,
                    "unit": "m-1",
                    "hardware_unit": "A",
                    "powerconverter": "srmag/ps-plateau/series/current",
                    "curves": {"type": "pyaml.magnet.inline_curve", "mat": PLATEAU.tolist()},
                },
            }
        ],
    }


def load_with_plateau_series(accelerator_from_fragments, calibrations: list[float]) -> Accelerator:
    """Load the live test configuration plus a series of two PLATEAU magnets on one power supply."""
    return accelerator_from_fragments("tests/config/sr_serialized_magnets_cs.yaml", plateau_series_fragment(calibrations))


# Point 1: the weight of a magnet must not depend on how far its curve is tabulated


@pytest.mark.parametrize(
    "other_curve",
    [
        pytest.param(LINEAR_UP_TO_200, id="same line tabulated up to 200 A"),
        pytest.param(LINEAR_EXTENDED, id="same line with one more point at 300 A"),
    ],
)
def test_the_compromise_does_not_depend_on_how_far_a_curve_is_tabulated(other_curve):
    # Step 1: two magnets with the same slope (1.0 at 100 A).
    #   In the reference series, both curves stop at 100 A.
    #   In the other series, the second curve is the same straight line, only tabulated further.
    reference = make_series([LINEAR, LINEAR], calibrations=[1.0, 1.0])
    other = make_series([LINEAR, other_curve], calibrations=[1.0, 1.0])

    # Step 2: an inconsistent request: magnet 0 alone would need 40 A, magnet 1 alone 60 A.
    requested = np.array([0.4, 0.6])

    # Step 3: the power-supply current computed from these strengths, for both series.
    reference_current = reference.compute_hardware_from_strengths(requested)
    other_current = other.compute_hardware_from_strengths(requested)

    # Expected: the same current (50 A). The two magnets are physically identical, so the end of a table, which
    # anybody can extend when a curve is measured again, must not change the compromise.
    assert reference_current == pytest.approx(50.0)
    assert other_current == pytest.approx(reference_current)


# Point 2: on a plateau, writing back the strengths that were read must not move the power supply


@pytest.mark.parametrize("current", [85.0, 100.0])
def test_writing_back_the_strengths_read_on_a_plateau_keeps_the_current(current):
    # Step 1: two PLATEAU magnets: from 80 A to 110 A the strength stays at 0.8.
    series = make_series([PLATEAU, PLATEAU], calibrations=[1.0, 1.0])

    # Step 2: the power supply is at `current`, on the plateau. Read the strengths and write them back, as an array
    #   holding both magnets does.
    requested = series.compute_strengths([current])
    new_current = series.compute_hardware_values_partial(np.array([current]), {0: requested[0], 1: requested[1]})[0]

    # Expected: the current does not move. Every current of the plateau gives the requested strengths, and the
    # present one is among them: there is no reason to move the power supply.
    assert new_current == pytest.approx(current)


def test_writing_back_the_strength_of_one_magnet_read_on_a_plateau_keeps_the_current():
    # Step 1: the same two PLATEAU magnets, the power supply at 85 A.
    series = make_series([PLATEAU, PLATEAU], calibrations=[1.0, 1.0])
    current = 85.0

    # Step 2: an array holding only magnet 0 writes back the strength it read.
    requested = series.compute_strengths([current])[0]
    new_current = series.compute_hardware_values_partial(np.array([current]), {0: requested})[0]

    # Expected: the current does not move, the present current is one of those giving the requested strength.
    assert new_current == pytest.approx(current)


@pytest.mark.parametrize("accessor", ["family.strengths", "family.strength", "magnet.strength", "array.strengths"])
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_every_accessor_keeps_the_current_when_writing_back_on_a_plateau(
    install_test_package, accelerator_from_fragments, accessor
):
    # Step 1: in live, a series of two PLATEAU magnets on one power supply, set at 85 A (on the plateau).
    sr = load_with_plateau_series(accelerator_from_fragments, calibrations=[1.0, 1.0])
    family = sr.live.serialized_magnet.get("plateauSeries")
    family.hardware.set(85.0)

    # Step 2: read a strength and write it back, through one accessor.
    if accessor == "family.strengths":
        family.strengths.set(family.strengths.get())
    elif accessor == "family.strength":
        family.strength.set(family.strength.get())
    elif accessor == "magnet.strength":
        magnet = sr.live.magnet.get("QF4A-C10")
        magnet.strength.set(magnet.strength.get())
    else:
        array = sr.live.magnets.get("PLATEAU_MAGNETS")
        array.strengths.set(array.strengths.get())

    # Expected: the power supply stays at 85 A whatever the accessor: every accessor follows the same rule.
    assert family.hardware.get() == pytest.approx(85.0)


# Point 3: the family strength of a series mixing polarities


def test_family_strength_does_not_depend_on_the_order_of_the_magnets():
    # Step 1: the same two LINEAR magnets, one of them wired in reverse, declared in both orders.
    #   Swapping the two magnets in the configuration swaps their calibrations and their polarities.
    declared_one_way = make_series([LINEAR, LINEAR], calibrations=[1.0, -1.0], polarities=[1, -1])
    declared_the_other_way = make_series([LINEAR, LINEAR], calibrations=[-1.0, 1.0], polarities=[-1, 1])

    # Step 2: read the family strength at 40 A.
    # Expected: the same value. Swapping two lines of the configuration changes nothing in the machine, so it must
    # not change the sign of the family strength.
    assert declared_one_way.compute_mean_strength(40.0) == pytest.approx(declared_the_other_way.compute_mean_strength(40.0))


def test_a_series_mixing_polarities_must_declare_them():
    # Step 1: two LINEAR magnets, the second one wired in reverse (calibration -1), without declaring its polarity.
    #   By default every polarity is +1: the family strength would add +0.4 and -0.4 and give 0 at any current.
    # Expected: an error when the series is built, asking to declare the polarity of the magnet wired in reverse.
    with pytest.raises(PyAMLException, match="declare polarities"):
        make_series([LINEAR, LINEAR], calibrations=[1.0, -1.0])
