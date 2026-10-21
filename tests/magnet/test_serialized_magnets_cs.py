import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.magnet.serialized_magnet import SerializedMagnets

CONFIG = "tests/config/sr_serialized_magnets_cs.yaml"
TANGO_DUMMY = [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}]


def _sub_strengths(family: SerializedMagnets, current: float) -> np.ndarray:
    return np.array([family.model.get_sub_model(i).compute_strengths([current])[0] for i in range(family.get_nb_magnets())])


# Current range of the excitation curve sr/magnet_models/QF1_strength.csv
QF1_CURRENT_RANGE = (0.0, 110.0)


def _normalized_residual(family: SerializedMagnets, current: float, requested, indices) -> float:
    """Return sum((f_i(I) - k_i) / span_i) over the requested magnets, span_i being the strength range of their curve."""
    total = 0.0
    for idx, strength in zip(indices, requested, strict=True):
        model = family.model.get_sub_model(idx)
        span = model.compute_strengths([QF1_CURRENT_RANGE[1]])[0] - model.compute_strengths([QF1_CURRENT_RANGE[0]])[0]
        total += (model.compute_strengths([current])[0] - strength) / span
    return total


@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_serialized_magnets_attach_to_control_system(install_test_package):
    sr: Accelerator = Accelerator.load(CONFIG)
    family: SerializedMagnets = sr.live.serialized_magnet.get("QF1A")
    magnets = family.get_magnets()

    assert family.get_nb_magnets() == 4
    assert [m.get_name() for m in magnets] == ["QF1A-C05", "QF1A-C06", "QF1A-C07", "QF1A-C08"]
    for m in magnets:
        assert sr.live.magnet.get(m.get_name()) is m


@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_serialized_magnets_share_power_supply(install_test_package):
    sr: Accelerator = Accelerator.load(CONFIG)
    family: SerializedMagnets = sr.live.serialized_magnet.get("QF1A")
    magnets = family.get_magnets()

    magnets[2].hardware.set(80.0)
    assert np.allclose([m.hardware.get() for m in magnets], 80.0)
    assert np.allclose([m.strength.get() for m in magnets], _sub_strengths(family, 80.0))

    # Setting the strength of one magnet drives the shared power supply with that magnet's own sub-model
    magnets[1].strength.set(0.5)
    current = family.model.get_sub_model(1).compute_hardware_values([0.5])[0]
    assert np.allclose([m.hardware.get() for m in magnets], current)
    assert magnets[1].strength.get() == pytest.approx(0.5)

    # The other family is on its own power supply
    assert np.allclose([m.hardware.get() for m in sr.live.serialized_magnet.get("QD2A").get_magnets()], 0.0)


@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_serialized_magnets_aggregator(install_test_package):
    sr: Accelerator = Accelerator.load(CONFIG)
    qf1a: SerializedMagnets = sr.live.serialized_magnet.get("QF1A")
    qd2a: SerializedMagnets = sr.live.serialized_magnet.get("QD2A")
    qf1a.get_magnets()[0].hardware.set(30.0)
    qd2a.get_magnets()[0].hardware.set(20.0)

    array = sr.live.magnets.get("ALL_SERIALIZED")
    expected = np.concatenate([_sub_strengths(qf1a, 30.0), _sub_strengths(qd2a, 20.0)])
    assert np.allclose(array.strengths.get(), expected)
    assert np.allclose(array.hardwares.get(), [30.0] * 4 + [20.0] * 3)

    # Doubling every magnet of a series moves its power supply to the current of the doubled strength (no 1/N dilution)
    array.strengths.set(2 * array.strengths.get())
    assert np.allclose(array.strengths.get(), 2 * expected)
    qf1a_current = qf1a.model.get_sub_model(0).compute_hardware_values([2 * expected[0]])[0]
    assert np.allclose(array.hardwares.get()[:4], qf1a_current)

    array.hardwares.set(array.hardwares.get())
    assert np.allclose(array.strengths.get(), 2 * expected)


MODES = ["design", "live"]


def _family(sr: Accelerator, mode: str, name: str = "QF1A") -> SerializedMagnets:
    return getattr(sr, mode).serialized_magnet.get(name)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_hardware_is_the_power_supply_current(install_test_package, mode):
    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    family.hardware.set(80.0)
    assert family.hardware.get() == pytest.approx(80.0)
    assert np.allclose([m.hardware.get() for m in family.get_magnets()], 80.0)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_set_of_get_does_not_change_the_machine(install_test_package, mode):
    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    magnet = family.get_magnets()[2]
    family.hardware.set(80.0)
    for accessor in [family.hardware, family.strength, magnet.hardware, magnet.strength]:
        accessor.set(accessor.get())
        assert family.hardware.get() == pytest.approx(80.0)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_strength_is_the_average_strength(install_test_package, mode):
    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    family.hardware.set(80.0)
    assert family.strength.get() == pytest.approx(np.mean(_sub_strengths(family, 80.0)))

    # QF1A has a different calibration factor per magnet: the requested value is the average strength
    family.strength.set(0.79)
    assert family.strength.get() == pytest.approx(0.79)
    assert np.mean([m.strength.get() for m in family.get_magnets()]) == pytest.approx(0.79)
    assert family.hardware.get() == pytest.approx(family.model.compute_hardware_from_mean_strength(0.79))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_magnet_strength_drives_the_series_with_its_own_submodel(install_test_package, mode):
    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    magnets = family.get_magnets()
    magnets[1].strength.set(0.5)
    current = family.model.get_sub_model(1).compute_hardware_values([0.5])[0]
    assert family.hardware.get() == pytest.approx(current)
    assert magnets[1].strength.get() == pytest.approx(0.5)
    assert np.allclose([m.strength.get() for m in magnets], _sub_strengths(family, current))


@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_design_and_live_agree(install_test_package):
    sr: Accelerator = Accelerator.load(CONFIG)
    design, live = _family(sr, "design"), _family(sr, "live")
    design.hardware.set(80.0)
    live.hardware.set(80.0)
    assert design.strength.get() == pytest.approx(live.strength.get())
    assert np.allclose(
        [m.strength.get() for m in design.get_magnets()],
        [m.strength.get() for m in live.get_magnets()],
    )


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_array_with_one_magnet_of_a_series_drives_the_series_with_its_own_submodel(install_test_package, mode, caplog):
    from pyaml.arrays.magnet_array import MagnetArray

    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    family.hardware.set(80.0)
    array = MagnetArray("ONE", [family.get_magnets()[1]])

    with caplog.at_level("WARNING"):
        array.strengths.set(np.array([0.5]))

    # Same as magnets[1].strength.set(0.5): I = f_1^-1(0.5), the other magnets follow as f_j(I)
    current = family.model.get_sub_model(1).compute_hardware_values([0.5])[0]
    assert family.hardware.get() == pytest.approx(current)
    assert np.allclose(family.strengths.get(), _sub_strengths(family, current))
    assert "Inconsistent strengths" not in caplog.text


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_array_with_consistent_magnets_of_a_series(install_test_package, mode):
    sr: Accelerator = Accelerator.load(CONFIG)
    qf1a, qd2a = _family(sr, mode, "QF1A"), _family(sr, mode, "QD2A")
    qf1a.hardware.set(80.0)
    qd2a.hardware.set(20.0)
    array = getattr(sr, mode).magnets.get("ALL_SERIALIZED")
    array.strengths.set(array.strengths.get())
    assert qf1a.hardware.get() == pytest.approx(80.0)
    assert qd2a.hardware.get() == pytest.approx(20.0)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_array_with_inconsistent_magnets_of_a_series(install_test_package, mode, caplog):
    sr: Accelerator = Accelerator.load(CONFIG)
    qf1a, qd2a = _family(sr, mode, "QF1A"), _family(sr, mode, "QD2A")
    qf1a.hardware.set(80.0)
    qd2a.hardware.set(20.0)
    array = getattr(sr, mode).magnets.get("ALL_SERIALIZED")
    strengths = array.strengths.get()
    requested = np.array([0.78, 0.79, 0.80, 0.81])
    strengths[:4] = requested
    with caplog.at_level("WARNING"):
        array.strengths.set(strengths)
    # Every magnet of QF1A is in the array: the power supply gets the I solving sum((f_i(I) - k_i) / span_i) == 0
    assert _normalized_residual(qf1a, qf1a.hardware.get(), requested, range(4)) == pytest.approx(0.0, abs=1e-9)
    assert qd2a.hardware.get() == pytest.approx(20.0)
    assert "Inconsistent strengths" in caplog.text


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_array_with_part_of_a_series_drives_the_series_from_the_requested_magnets_only(install_test_package, mode):
    from pyaml.arrays.magnet_array import MagnetArray

    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    family.hardware.set(80.0)
    magnets = family.get_magnets()
    array = MagnetArray("PART", [magnets[1], magnets[2]])
    requested = np.array([0.78, 0.82])

    array.strengths.set(requested)

    # Only magnets 1 and 2 define I: sum((f_i(I) - k_i) / span_i) == 0 over them. Magnets 0 and 3 follow as f_j(I)
    current = family.hardware.get()
    assert _normalized_residual(family, current, requested, [1, 2]) == pytest.approx(0.0, abs=1e-9)
    assert np.allclose(family.strengths.get(), _sub_strengths(family, current))


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_strength_outside_the_excitation_curve_is_clamped_with_a_warning(install_test_package, mode, caplog):
    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    family.hardware.set(80.0)
    # Highest current of the QF1 excitation curve
    curve_end = family.model.get_sub_model(0).compute_hardware_values([1e3])[0]

    with caplog.at_level("WARNING"):
        family.strengths.set(np.full(family.get_nb_magnets(), 1e3))

    assert family.hardware.get() == pytest.approx(curve_end)
    assert "outside the range" in caplog.text
    assert "Inconsistent strengths" not in caplog.text


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_strengths_and_hardwares_read_every_magnet(install_test_package, mode):
    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    family.hardware.set(80.0)

    # One call reads every magnet of the series: k_i = f_i(I), and the shared current I
    assert np.allclose(family.strengths.get(), [m.strength.get() for m in family.get_magnets()])
    assert np.allclose(family.strengths.get(), _sub_strengths(family, 80.0))
    assert np.allclose(family.hardwares.get(), 80.0)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_strengths_set_balances_the_normalized_errors(install_test_package, mode, caplog):
    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    family.hardware.set(80.0)
    requested = np.array([0.78, 0.79, 0.80, 0.81])

    with caplog.at_level("WARNING"):
        family.strengths.set(requested)

    # One power supply: the series gets the I solving sum((f_i(I) - k_i) / span_i) == 0
    current = family.hardware.get()
    assert _normalized_residual(family, current, requested, range(4)) == pytest.approx(0.0, abs=1e-9)
    # QF1A has a different calibration factor per magnet: these strengths cannot all be reached with one current
    assert "Inconsistent strengths" in caplog.text


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_hardwares_set_applies_the_average_current(install_test_package, mode):
    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)

    family.hardwares.set(np.array([79.0, 80.0, 81.0, 84.0]))

    assert family.hardware.get() == pytest.approx(81.0)
    assert np.allclose(family.hardwares.get(), 81.0)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_family_array_set_of_get_does_not_change_the_machine(install_test_package, mode, caplog):
    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    family.hardware.set(80.0)
    with caplog.at_level("WARNING"):
        for accessor in [family.strengths, family.hardwares]:
            accessor.set(accessor.get())
            assert family.hardware.get() == pytest.approx(80.0)
    assert "Inconsistent strengths" not in caplog.text


# QF1A on a power supply limited to [0, 90] A, with an array holding magnets C06 and C07 only
RANGE_CONFIG = "tests/config/sr_serialized_magnets_range.yaml"


@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_power_supply_range_protects_every_write_to_a_series(install_test_package):
    sr: Accelerator = Accelerator.load(RANGE_CONFIG)
    family: SerializedMagnets = sr.live.serialized_magnet.get("QF1A")
    magnets = family.get_magnets()
    family.hardware.set(80.0)
    # Strengths that need 100 A, outside the range of the power supply
    too_strong = _sub_strengths(family, 100.0)

    writes = [
        lambda: sr.live.magnets.get("QF1A_PART").strengths.set(too_strong[[1, 2]]),
        lambda: family.strengths.set(too_strong),
        lambda: family.strength.set(np.mean(too_strong)),
        lambda: magnets[1].strength.set(too_strong[1]),
        lambda: family.hardware.set(100.0),
    ]
    for write in writes:
        with pytest.raises(PyAMLException):
            write()
        # Nothing is written: the series stays at 80 A
        assert family.hardware.get() == pytest.approx(80.0)


@pytest.mark.parametrize("install_test_package", TANGO_DUMMY, indirect=True)
def test_array_with_part_of_a_series_within_the_power_supply_range(install_test_package):
    sr: Accelerator = Accelerator.load(RANGE_CONFIG)
    family: SerializedMagnets = sr.live.serialized_magnet.get("QF1A")
    family.hardware.set(80.0)
    within = _sub_strengths(family, 70.0)

    sr.live.magnets.get("QF1A_PART").strengths.set(within[[1, 2]])

    # Magnets C06 and C07 ask for 70 A, magnets C05 and C08 follow
    assert family.hardware.get() == pytest.approx(70.0)
    assert np.allclose(family.strengths.get(), within)
