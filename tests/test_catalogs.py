import numpy as np
import pytest

from pyaml import PyAMLConfigException, PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.configuration.catalog import Catalog, CatalogConfigModel, CatalogResolver
from pyaml.control.deviceaccess import DeviceAccess


class FakeDeviceAccess(DeviceAccess):
    def __init__(self, name: str, unit: str = ""):
        self._name = name
        self._unit = unit

    def name(self) -> str:
        return self._name

    def measure_name(self) -> str:
        return self._name

    def set(self, value):
        return None

    def set_and_wait(self, value):
        return None

    def get(self):
        return None

    def readback(self):
        return None

    def unit(self) -> str:
        return self._unit

    def get_range(self) -> list[float]:
        return []

    def check_device_availability(self) -> bool:
        return True


class DummyCatalogBinding(CatalogResolver):
    def __init__(self, control_system_name: str):
        self._control_system_name = control_system_name

    def resolve(self, key: str) -> DeviceAccess:
        return FakeDeviceAccess(name=f"{self._control_system_name}:{key}", unit="")


class DummyContextCatalog(Catalog):
    def attach_control_system(self, control_system):
        return DummyCatalogBinding(control_system.name())

    def resolve(self, key: str) -> DeviceAccess:
        raise AssertionError("Shared catalog object must not resolve keys directly")


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
                        "type": "tango.pyaml.static_catalog",
                        "name": "inline-live",
                        "entries": [
                            {
                                "type": "tango.pyaml.static_catalog_entry",
                                "key": "BPM_C02-01/x",
                                "device": {
                                    "type": "tango.pyaml.attribute_read_only",
                                    "attribute": "srdiag/bpm/c02-01/SA_HPosition",
                                    "unit": "mm",
                                },
                            },
                            {
                                "type": "tango.pyaml.static_catalog_entry",
                                "key": "BPM_C02-01/y",
                                "device": {
                                    "type": "tango.pyaml.attribute_read_only",
                                    "attribute": "srdiag/bpm/c02-01/SA_VPosition",
                                    "unit": "mm",
                                },
                            },
                        ],
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
    from tango.pyaml.static_catalog import StaticCatalog

    attached = []
    original = StaticCatalog.attach_control_system

    def record_attachment(self, control_system):
        attached.append((self.get_name(), control_system.name()))
        return original(self, control_system)

    monkeypatch.setattr(StaticCatalog, "attach_control_system", record_attachment)

    sr = Accelerator.load("tests/config/catalog_named.yaml")

    assert sr.live.get_catalog() is sr.ops.get_catalog()
    assert attached == [("device-catalog", "live"), ("device-catalog", "ops")]


def test_shared_catalog_can_bind_different_resolvers_per_control_system():
    catalog = DummyContextCatalog(CatalogConfigModel(name="contextual"))

    class DummyControlSystem:
        def __init__(self, name: str):
            self._name = name
            self._catalog = None
            self._catalog_resolver = None

        def name(self) -> str:
            return self._name

        def set_catalog(self, bound_catalog: Catalog | None):
            self._catalog = bound_catalog
            self._catalog_resolver = bound_catalog.attach_control_system(self) if bound_catalog is not None else None

        def get_catalog(self):
            return self._catalog

        def resolve(self, key: str) -> DeviceAccess:
            return self._catalog_resolver.resolve(key)

    live = DummyControlSystem("live")
    ops = DummyControlSystem("ops")
    live.set_catalog(catalog)
    ops.set_catalog(catalog)

    assert live.get_catalog() is ops.get_catalog() is catalog
    assert live.resolve("BPM/X").name() == "live:BPM/X"
    assert ops.resolve("BPM/X").name() == "ops:BPM/X"


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
                        "type": "tango.pyaml.static_catalog",
                        "name": "device-catalog",
                        "entries": [
                            {
                                "type": "tango.pyaml.static_catalog_entry",
                                "key": "BPM_C03-01/x",
                                "device": {
                                    "type": "tango.pyaml.attribute_read_only",
                                    "attribute": "srdiag/bpm/c03-01/SA_HPosition",
                                    "unit": "mm",
                                },
                            }
                        ],
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
                        "type": "tango.pyaml.static_catalog",
                        "name": "duplicate",
                        "entries": [
                            {
                                "type": "tango.pyaml.static_catalog_entry",
                                "key": "QF1/current",
                                "device": {
                                    "type": "tango.pyaml.attribute",
                                    "attribute": "sr/test/one",
                                    "unit": "A",
                                },
                            }
                        ],
                    },
                    {
                        "type": "tango.pyaml.static_catalog",
                        "name": "duplicate",
                        "entries": [
                            {
                                "type": "tango.pyaml.static_catalog_entry",
                                "key": "QF2/current",
                                "device": {
                                    "type": "tango.pyaml.attribute",
                                    "attribute": "sr/test/two",
                                    "unit": "A",
                                },
                            }
                        ],
                    },
                ],
            },
        )


def test_duplicate_static_catalog_entry_keys_raise_config_error():
    with pytest.raises(PyAMLConfigException, match="duplicate key 'duplicated/key'"):
        Accelerator.load("tests/config/bad_catalog_duplicate_key.yaml")


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_indexed_catalog_entry_extracts_scalar_from_vector_attribute(install_test_package):
    """
    Verify that a catalog can map two keys to different indices of the same
    vector attribute.  The BPM sees two independent scalar DeviceAccess objects
    (one per axis) even though the hardware exposes a single position vector.
    The indexing is fully transparent to pyAML — it happens in the CS backend.
    """
    from tango.pyaml.attribute_store import set_attribute

    set_attribute("srdiag/bpm/c01-04/Position", [1.5, -0.3], unit="mm")

    sr = Accelerator.from_dict(
        {
            "type": "pyaml.accelerator",
            "facility": "ESRF",
            "machine": "sr",
            "energy": 6e9,
            "data_folder": "/data/store",
            "catalogs": [
                {
                    "type": "tango.pyaml.static_catalog",
                    "name": "bpm-catalog",
                    "entries": [
                        {
                            "type": "tango.pyaml.static_catalog_entry",
                            "key": "bpm/SA_HPosition",
                            "device": {
                                "type": "tango.pyaml.attribute",
                                "attribute": "srdiag/bpm/c01-04/Position",
                                "index": 0,
                                "unit": "mm",
                            },
                        },
                        {
                            "type": "tango.pyaml.static_catalog_entry",
                            "key": "bpm/SA_VPosition",
                            "device": {
                                "type": "tango.pyaml.attribute",
                                "attribute": "srdiag/bpm/c01-04/Position",
                                "index": 1,
                                "unit": "mm",
                            },
                        },
                    ],
                }
            ],
            "controls": [
                {
                    "type": "tango.pyaml.controlsystem",
                    "tango_host": "ebs-simu-3:10000",
                    "name": "live",
                    "catalog": "bpm-catalog",
                }
            ],
            "devices": [
                {
                    "type": "pyaml.bpm.bpm",
                    "name": "BPM_TEST",
                    "model": {
                        "type": "pyaml.bpm.bpm_simple_model",
                        "x_pos": "bpm/SA_HPosition",
                        "y_pos": "bpm/SA_VPosition",
                    },
                }
            ],
        }
    )

    bpm = sr.live.get_bpm("BPM_TEST")
    positions = bpm.positions.get()
    assert np.isclose(positions[0], 1.5)
    assert np.isclose(positions[1], -0.3)
