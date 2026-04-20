import numpy as np
import pytest

from pyaml import PyAMLConfigException, PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.configuration.static_catalog import StaticCatalog


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_named_catalog_is_shared_and_resolves_devices(install_test_package):
    sr = Accelerator.load("tests/config/catalog_named.yaml")

    shared_catalog = sr.get_catalog("device-catalog")
    assert sr.live.get_catalog() is shared_catalog
    assert sr.ops.get_catalog() is shared_catalog

    bpm = sr.live.get_bpm("BPM_C01-01")
    assert np.allclose(bpm.positions.get(), np.array([0.0, 0.0]))
    bpm.offset.set(np.array([0.1, 0.2]))
    assert np.allclose(bpm.offset.get(), np.array([0.1, 0.2]))
    bpm.tilt.set(0.01)
    assert bpm.tilt.get() == 0.01

    quad = sr.live.get_magnet("QF1A-C01")
    quad.hardware.set(1.2)
    assert quad.hardware.get() == 1.2

    cfm_h = sr.live.get_magnet("SH1A-C01-H")
    cfm_h.hardware.set(2.5)
    assert cfm_h.hardware.get() == 2.5

    tune_monitor = sr.live.get_betatron_tune_monitor("BETATRON_TUNE")
    assert np.allclose(tune_monitor.tune.get(), np.array([0.0, 0.0]))

    rf = sr.live.get_rf_plant("RF")
    rf.frequency.set(1.23)
    assert rf.frequency.get() == 1.23


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_inline_catalog_is_supported(install_test_package):
    sr = Accelerator.from_dict(
        {
            "type": "pyaml.accelerator",
            "facility": "ESRF",
            "machine": "sr",
            "energy": 6e9,
            "data_folder": "/data/store",
            "controls": [
                {
                    "type": "tango.pyaml.controlsystem",
                    "tango_host": "ebs-simu-3:10000",
                    "name": "live",
                    "catalog": {
                        "type": "pyaml.configuration.static_catalog",
                        "name": "inline-live",
                        "refs": {
                            "BPM_C02-01/x": {
                                "type": "tango.pyaml.attribute_read_only",
                                "attribute": "srdiag/bpm/c02-01/SA_HPosition",
                                "unit": "mm",
                            },
                            "BPM_C02-01/y": {
                                "type": "tango.pyaml.attribute_read_only",
                                "attribute": "srdiag/bpm/c02-01/SA_VPosition",
                                "unit": "mm",
                            },
                        },
                    },
                }
            ],
            "devices": [
                {
                    "type": "pyaml.bpm.bpm",
                    "name": "BPM_C02-01",
                    "model": {
                        "type": "pyaml.bpm.bpm_simple_model",
                        "x_pos": "BPM_C02-01/x",
                        "y_pos": "BPM_C02-01/y",
                    },
                }
            ],
        }
    )

    assert sr.live.get_catalog().get_name() == "inline-live"
    bpm = sr.live.get_bpm("BPM_C02-01")
    assert np.allclose(bpm.positions.get(), np.array([0.0, 0.0]))


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_is_notified_when_attached_to_control_systems(install_test_package, monkeypatch):
    attached = []
    original = StaticCatalog.attach_control_system

    def record_attachment(self, control_system):
        attached.append((self.get_name(), control_system.name()))
        return original(self, control_system)

    monkeypatch.setattr(StaticCatalog, "attach_control_system", record_attachment)

    sr = Accelerator.load("tests/config/catalog_named.yaml")

    assert sr.live.get_catalog() is sr.ops.get_catalog()
    assert attached == [("device-catalog", "live"), ("device-catalog", "ops")]


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_unknown_catalog_name_raises_config_error(install_test_package):
    with pytest.raises(PyAMLConfigException, match="catalog missing-catalog not defined"):
        Accelerator.from_dict(
            {
                "type": "pyaml.accelerator",
                "facility": "ESRF",
                "machine": "sr",
                "energy": 6e9,
                "data_folder": "/data/store",
                "controls": [
                    {
                        "type": "tango.pyaml.controlsystem",
                        "tango_host": "ebs-simu-3:10000",
                        "name": "live",
                        "catalog": "missing-catalog",
                    }
                ],
                "devices": [],
            }
        )


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_unresolved_catalog_key_raises_runtime_error(install_test_package):
    with pytest.raises(
        PyAMLConfigException,
        match="Catalog 'device-catalog' cannot resolve key 'BPM_C03-01/y'",
    ):
        Accelerator.from_dict(
            {
                "type": "pyaml.accelerator",
                "facility": "ESRF",
                "machine": "sr",
                "energy": 6e9,
                "data_folder": "/data/store",
                "catalogs": [
                    {
                        "type": "pyaml.configuration.static_catalog",
                        "name": "device-catalog",
                        "refs": {
                            "BPM_C03-01/x": {
                                "type": "tango.pyaml.attribute_read_only",
                                "attribute": "srdiag/bpm/c03-01/SA_HPosition",
                                "unit": "mm",
                            }
                        },
                    }
                ],
                "controls": [
                    {
                        "type": "tango.pyaml.controlsystem",
                        "tango_host": "ebs-simu-3:10000",
                        "name": "live",
                        "catalog": "device-catalog",
                    }
                ],
                "devices": [
                    {
                        "type": "pyaml.bpm.bpm",
                        "name": "BPM_C03-01",
                        "model": {
                            "type": "pyaml.bpm.bpm_simple_model",
                            "x_pos": "BPM_C03-01/x",
                            "y_pos": "BPM_C03-01/y",
                        },
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_duplicate_top_level_catalog_names_raise_config_error(install_test_package):
    with pytest.raises(PyAMLConfigException, match="catalog duplicate already defined"):
        Accelerator.from_dict(
            {
                "type": "pyaml.accelerator",
                "facility": "ESRF",
                "machine": "sr",
                "energy": 6e9,
                "data_folder": "/data/store",
                "devices": [],
                "catalogs": [
                    {
                        "type": "pyaml.configuration.static_catalog",
                        "name": "duplicate",
                        "refs": {
                            "QF1/current": {
                                "type": "tango.pyaml.attribute",
                                "attribute": "sr/test/one",
                                "unit": "A",
                            }
                        },
                    },
                    {
                        "type": "pyaml.configuration.static_catalog",
                        "name": "duplicate",
                        "refs": {
                            "QF2/current": {
                                "type": "tango.pyaml.attribute",
                                "attribute": "sr/test/two",
                                "unit": "A",
                            }
                        },
                    },
                ],
            },
        )


def test_duplicate_static_catalog_keys_raise_yaml_error():
    with pytest.raises(PyAMLException, match="duplicate key"):
        Accelerator.load("tests/config/bad_catalog_duplicate_key.yaml")
