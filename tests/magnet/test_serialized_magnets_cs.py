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
