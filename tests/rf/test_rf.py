import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLException
from pyaml.lattice.simulator import Simulator


def test_rf():
    sr: Accelerator = Accelerator.load("tests/config/EBS_rf.yaml", ignore_external=True)

    sr.design.rf.frequency.set(3.523e8)

    # Check that frequency has been applied on all cavities
    ring = sr.design.get_lattice()
    for e in ring:
        if e.FamName.startswith("CAV"):
            assert e.Frequency == 3.523e8

    sr.design.rf.voltage.set(10.0e6)

    # Check that voltage has been applied on all cavities
    ring = sr.design.get_lattice()
    for e in ring:
        if e.FamName.startswith("CAV"):
            assert np.isclose(e.Voltage, 10.0e6 / 13.0)

    if False:
        sr.live.rf.frequency.set(3.523721693993786e8)
        sr.live.rf.voltage.set(6.5e6)
        assert np.isclose(sr.live.rf.frequency.get(), 3.523721693993786e8)
        assert np.isclose(sr.live.rf.voltage.get(), 6.5e6)


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_rf_multi(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/EBS_rf_multi.yaml")

    # Simulator

    sr.design.rf.frequency.set(3.523e8)

    # Check that frequency has been applied on all cavities
    ring = sr.design.get_lattice()
    for e in ring:
        if e.FamName.startswith("CAV"):
            if e.FamName == "CAV_C25_03":
                # Harmonic cavity
                assert np.isclose(e.Frequency, 1.4092e9)
            else:
                assert e.Frequency == 3.523e8

    RFTRA_HARMONIC = sr.design.rf.transmitter.get("RFTRA_HARMONIC")
    RFTRA_HARMONIC.voltage.set(300e3)
    sr.design.rf.voltage.set(12e6)

    for e in ring:
        if e.FamName.startswith("CAV"):
            if e.FamName == "CAV_C25_03":
                # Harmonic cavity
                assert np.isclose(e.Voltage, 300e3)
            else:
                assert np.isclose(e.Voltage, 1e6)

    # Control system
    RF1 = sr.live.rf.transmitter.get("RFTRA1")
    RF2 = sr.live.rf.transmitter.get("RFTRA2")
    RFTRA_HARMONIC = sr.live.rf.transmitter.get("RFTRA_HARMONIC")

    sr.live.rf.frequency.set(3.523e8)
    RFTRA_HARMONIC.voltage.set(300e3)
    sr.live.rf.voltage.set(12e6)

    assert np.isclose(RF1.voltage.get(), 10e6)
    assert np.isclose(RF2.voltage.get(), 2e6)
    assert np.isclose(RFTRA_HARMONIC.voltage.get(), 3e5)


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_rf_multi_notrans(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/EBS_rf_notrans.yaml")

    # Simulator
    sr.design.rf.frequency.set(3.523e8)
    sr.design.rf.voltage.set(10e6)
    # Check that frequency and voltage has been applied on all cavities
    ring = sr.design.get_lattice()
    for e in ring:
        if e.FamName.startswith("CAV"):
            assert np.isclose(e.Frequency, 3.523e8)
            assert np.isclose(e.Voltage, 10e6 / 13.0)

    # Control system
    sr.live.rf.frequency.set(3.523e8)
    with pytest.raises(PyAMLException) as exc:
        sr.live.rf.voltage.set(10e6)
    assert "has no transmitter device defined" in str(exc)

    # Check that frequency and voltage has been applied on the masterclock device
    assert np.isclose(sr.live.rf.frequency.get(), 3.523e8)


def test_masterclock_returns_the_default_rf_plant():
    sr: Accelerator = Accelerator.load("tests/config/EBS_rf.yaml", ignore_external=True)

    assert sr.design.rf.masterclock is sr.design.rf.get("DEFAULT_RF_PLANT")


def test_frequency_and_voltage_are_masterclock_aliases():
    sr: Accelerator = Accelerator.load("tests/config/EBS_rf.yaml", ignore_external=True)

    assert sr.design.rf.frequency is sr.design.rf.masterclock.frequency
    assert sr.design.rf.voltage is sr.design.rf.masterclock.voltage

    sr.design.rf.masterclock.frequency.set(3.6e8)
    assert sr.design.rf.frequency.get() == pytest.approx(3.6e8)

    sr.design.rf.frequency.set(3.523e8)
    assert sr.design.rf.masterclock.frequency.get() == pytest.approx(3.523e8)


def test_masterclock_raises_when_default_rf_plant_missing(ebs_lattice_file):
    holder = Simulator(name="empty", lattice=str(ebs_lattice_file))

    with pytest.raises(PyAMLException) as exc:
        _ = holder.rf.masterclock
    assert "DEFAULT_RF_PLANT" in str(exc.value)


def test_simple_rf_access():
    sr: Accelerator = Accelerator.load("tests/config/EBS_rf.yaml", ignore_external=True)

    masterclock = sr.design.rf.masterclock
    masterclock.frequency.set(499.654e6)
    masterclock.voltage.set(2.5e6)

    same_frequency = sr.design.rf.frequency
    assert same_frequency.get() == pytest.approx(499.654e6)

    # No second RF plant is configured in this fixture: reuse the existing
    # one to check that named lookup keeps working alongside the masterclock.
    default_rf_plant = sr.design.rf.get("DEFAULT_RF_PLANT")
    assert default_rf_plant is masterclock
