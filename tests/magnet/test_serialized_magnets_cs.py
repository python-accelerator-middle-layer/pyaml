import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.magnet.serialized_magnet import SerializedMagnets

CONFIG = "tests/config/sr_serialized_magnets_cs.yaml"
TANGO_DUMMY = [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}]


def _sub_strengths(family: SerializedMagnets, current: float) -> np.ndarray:
    return np.array([family.model.get_sub_model(i).compute_strengths([current])[0] for i in range(family.get_nb_magnets())])


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
def test_array_with_one_magnet_of_a_series_moves_the_whole_series(install_test_package, mode):
    from pyaml.arrays.magnet_array import MagnetArray

    sr: Accelerator = Accelerator.load(CONFIG)
    family = _family(sr, mode)
    family.hardware.set(80.0)
    array = MagnetArray("ONE", [family.get_magnets()[1]])
    array.strengths.set(np.array([0.5]))
    current = family.model.get_sub_model(1).compute_hardware_values([0.5])[0]
    assert family.hardware.get() == pytest.approx(current)
    assert array.strengths.get() == pytest.approx([0.5])


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
    # The power supply gets the mean of the currents asked by the magnets of the series
    expected = np.mean([qf1a.model.get_sub_model(i).compute_hardware_values([s])[0] for i, s in enumerate(requested)])
    assert qf1a.hardware.get() == pytest.approx(expected)
    assert qd2a.hardware.get() == pytest.approx(20.0)
    assert "Inconsistent strengths" in caplog.text
