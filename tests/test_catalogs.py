import numpy as np
import pytest

from pyaml import PyAMLConfigException
from pyaml.accelerator import Accelerator


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
                    "x_pos": "BPM_C02-01/x",
                    "y_pos": "BPM_C02-01/y",
                }
            ],
        }
    )

    bpm = sr.live.get_bpm("BPM_C02-01")
    assert np.allclose(bpm.positions.get(), np.array([0.0, 0.0]))


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_unresolved_catalog_key_raises_runtime_error(install_test_package):
    with pytest.raises(
        PyAMLConfigException,
        match="Catalog cannot resolve key 'BPM_C03-01/y'",
    ):
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
                        "catalog": {
                            "type": "tango.pyaml.static_catalog",
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
                        },
                    }
                ],
                "devices": [
                    {
                        "type": "pyaml.bpm.bpm",
                        "name": "BPM_C03-01",
                        "x_pos": "BPM_C03-01/x",
                        "y_pos": "BPM_C03-01/y",
                    }
                ],
            }
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
            "controls": [
                {
                    "type": "tango.pyaml.controlsystem",
                    "tango_host": "ebs-simu-3:10000",
                    "name": "live",
                    "catalog": {
                        "type": "tango.pyaml.static_catalog",
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
                    },
                }
            ],
            "devices": [
                {
                    "type": "pyaml.bpm.bpm",
                    "name": "BPM_TEST",
                    "x_pos": "bpm/SA_HPosition",
                    "y_pos": "bpm/SA_VPosition",
                }
            ],
        }
    )

    bpm = sr.live.get_bpm("BPM_TEST")
    positions = bpm.positions.get()
    assert np.isclose(positions[0], 1.5)
    assert np.isclose(positions[1], -0.3)
