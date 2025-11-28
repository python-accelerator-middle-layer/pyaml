import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLException
from pyaml.configuration.factory import Factory


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_rf(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/EBS_rf.yaml")
    RF = sr.design.get_rf_plant("RF")

    RF.frequency.set(3.523e8)

    # Check that frequency has been applied on all cavities
    ring = sr.design.get_lattice()
    for e in ring:
        if e.FamName.startswith("CAV"):
            assert e.Frequency == 3.523e8

    RF.voltage.set(10.0e6)

    # Check that voltage has been applied on all cavities
    ring = sr.design.get_lattice()
    for e in ring:
        if e.FamName.startswith("CAV"):
            assert np.isclose(e.Voltage, 10.0e6 / 13.0)

    if False:
        RF = sr.live.get_rf_plant("RF")
        RF.frequency.set(3.523721693993786e8)
        RF.voltage.set(6.5e6)
        assert np.isclose(RF.frequency.get(), 3.523721693993786e8)
        assert np.isclose(RF.voltage.get(), 6.5e6)

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_rf_multi(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/EBS_rf_multi.yaml")

    # Simulator
    RF = sr.design.get_rf_plant("RF")

    RF.frequency.set(3.523e8)

    # Check that frequency has been applied on all cavities
    ring = sr.design.get_lattice()
    for e in ring:
        if e.FamName.startswith("CAV"):
            if e.FamName == "CAV_C25_03":
                # Harmonic cavity
                assert np.isclose(e.Frequency, 1.4092e9)
            else:
                assert e.Frequency == 3.523e8

    RFTRA_HARMONIC = sr.design.get_rf_trasnmitter("RFTRA_HARMONIC")
    RFTRA_HARMONIC.voltage.set(300e3)
    RF.voltage.set(12e6)

    for e in ring:
        if e.FamName.startswith("CAV"):
            if e.FamName == "CAV_C25_03":
                # Harmonic cavity
                assert np.isclose(e.Voltage, 300e3)
            else:
                assert np.isclose(e.Voltage, 1e6)

    # Control system
    RF = sr.live.get_rf_plant("RF")
    RF1 = sr.live.get_rf_trasnmitter("RFTRA1")
    RF2 = sr.live.get_rf_trasnmitter("RFTRA2")
    RFTRA_HARMONIC = sr.live.get_rf_trasnmitter("RFTRA_HARMONIC")

    RF.frequency.set(3.523e8)
    RFTRA_HARMONIC.voltage.set(300e3)
    RF.voltage.set(12e6)

    assert np.isclose(RF1._cfg.voltage.get(), 10e6)
    assert np.isclose(RF2._cfg.voltage.get(), 2e6)
    assert np.isclose(RFTRA_HARMONIC._cfg.voltage.get(), 3e5)

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_rf_multi_notrans(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/EBS_rf_notrans.yaml")

    # Simulator
    RF = sr.design.get_rf_plant("RF")
    RF.frequency.set(3.523e8)
    RF.voltage.set(10e6)
    # Check that frequency and voltage has been applied on all cavities
    ring = sr.design.get_lattice()
    for e in ring:
        if e.FamName.startswith("CAV"):
            assert np.isclose(e.Frequency, 3.523e8)
            assert np.isclose(e.Voltage, 10e6 / 13.0)

    # Control system
    RF = sr.live.get_rf_plant("RF")
    RF.frequency.set(3.523e8)
    with pytest.raises(PyAMLException) as exc:
        RF.voltage.set(10e6)
    assert "has no trasmitter device defined" in str(exc)

    # Check that frequency and voltage has been applied on the masterclock device
    assert np.isclose(RF.frequency.get(), 3.523e8)

    Factory.clear()
