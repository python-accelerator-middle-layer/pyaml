import numpy as np
import pytest

from pyaml.accelerator import Accelerator


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_tilt(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")
    bpm = sr.live.diagnostic.bpm.get("BPM_C01-01")
    print(bpm.tilt.get())

    assert bpm.tilt.get() == 0
    bpm.tilt.set(0.01)
    assert bpm.tilt.get() == 0.01


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_offset(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")
    bpm = sr.live.diagnostic.bpm.get("BPM_C01-01")

    assert bpm.offset.get()[0] == 0
    assert bpm.offset.get()[1] == 0
    bpm.offset.set(np.array([0.1, 0.2]))
    assert bpm.offset.get()[0] == 0.1
    assert bpm.offset.get()[1] == 0.2
    assert np.allclose(bpm.positions.get(), np.array([0.0, 0.0]))


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_position(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")
    bpm = sr.live.diagnostic.bpm.get("BPM_C01-01")
    bpm_simple = sr.live.diagnostic.bpm.get("BPM_C01-02")

    assert np.allclose(bpm.positions.get(), np.array([0.0, 0.0]))
    assert np.allclose(bpm_simple.positions.get(), np.array([0.0, 0.0]))


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_get_devices_returns_attached_devices(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")

    devs = sr.live.get_devices_access(["srdiag/bpm/c01-01/SA_HPosition", "srdiag/bpm/c01-01/SA_VPosition"])

    assert devs[0].name() == "//ebs-simu-3:10000/srdiag/bpm/c01-01/SA_HPosition"
    assert devs[1].name() == "//ebs-simu-3:10000/srdiag/bpm/c01-01/SA_VPosition"


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_get_device_accepts_backend_config_model(install_test_package):
    from tango.pyaml.attribute import ConfigModel as AttributeConfigModel

    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")

    dev = sr.live.get_device_access(AttributeConfigModel(attribute="srdiag/bpm/c01-05/SA_HPosition", unit="mm"))

    assert dev.name() == "//ebs-simu-3:10000/srdiag/bpm/c01-05/SA_HPosition"
    assert dev.unit() == "mm"


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_position_indexed(install_test_package):
    from tango.pyaml.attribute_store import set_attribute

    set_attribute("srdiag/bpm/c01-04/Position", [0.0, 1.0], unit="mm")

    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")
    bpm = sr.live.diagnostic.bpm.get("BPM_C01-04")

    assert np.allclose(bpm.positions.get(), np.array([0.0, 1.0]))


def _single_plane_bpm_config() -> dict:
    """Two full BPMs and one vertical-only XBPM, grouped in one BPM array."""
    entries = []
    for key in ["c01-01/H", "c01-01/V", "c01-02/H", "c01-02/V", "xbpm/V"]:
        entries.append(
            {
                "type": "tango.pyaml.static_catalog_entry",
                "key": key,
                "device": {"type": "tango.pyaml.attribute_read_only", "attribute": f"sr/bpm/{key}", "unit": "mm"},
            }
        )
    return {
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
                "catalog": {"type": "tango.pyaml.static_catalog", "entries": entries},
            }
        ],
        "arrays": [{"type": "pyaml.arrays.bpm", "name": "BPM", "elements": ["BPM_1", "BPM_2", "XBPM"]}],
        "devices": [
            {"type": "pyaml.diagnostics.bpm.bpm", "name": "BPM_1", "x_pos": "c01-01/H", "y_pos": "c01-01/V"},
            {"type": "pyaml.diagnostics.bpm.bpm", "name": "BPM_2", "x_pos": "c01-02/H", "y_pos": "c01-02/V"},
            {"type": "pyaml.diagnostics.bpm.bpm", "name": "XBPM", "y_pos": "xbpm/V"},
        ],
    }


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_single_plane(install_test_package):
    from tango.pyaml.attribute_store import set_attribute

    set_attribute("sr/bpm/xbpm/V", 0.3, unit="mm")
    sr = Accelerator.from_dict(_single_plane_bpm_config())
    xbpm = sr.live.diagnostic.bpm.get("XBPM")

    pos = xbpm.positions.get()
    assert np.isnan(pos[0])
    assert pos[1] == pytest.approx(0.3)
    assert xbpm.positions.unit() == "mm"


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_array_with_single_plane_bpm(install_test_package):
    from tango.pyaml.attribute_store import set_attribute

    for name, value in [("c01-01/H", 0.1), ("c01-01/V", -0.1), ("c01-02/H", 0.2), ("c01-02/V", -0.2), ("xbpm/V", 0.3)]:
        set_attribute(f"sr/bpm/{name}", value, unit="mm")
    sr = Accelerator.from_dict(_single_plane_bpm_config())
    bpms = sr.live.diagnostic.bpms.get("BPM")

    pos = bpms.positions.get()
    assert pos.shape == (3, 2)
    assert np.isnan(pos[2, 0])
    assert np.allclose(pos[:2], [[0.1, -0.1], [0.2, -0.2]])
    assert pos[2, 1] == pytest.approx(0.3)

    h = bpms.h.get()
    assert np.allclose(h[:2], [0.1, 0.2])
    assert np.isnan(h[2])
    assert np.allclose(bpms.v.get(), [-0.1, -0.2, 0.3])

    # The missing plane must not disable the grouped reads
    agg, aggh, aggv = sr.live.create_bpm_aggregators(list(bpms))
    assert [agg.nb_device(), aggh.nb_device(), aggv.nb_device()] == [6, 3, 3]
    assert np.allclose(agg.get(), pos.flatten(), equal_nan=True)
    assert np.allclose(aggh.get(), h, equal_nan=True)
    assert np.allclose(aggv.get(), [-0.1, -0.2, 0.3])


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_array_without_horizontal_plane(install_test_package):
    from tango.pyaml.attribute_store import set_attribute

    set_attribute("sr/bpm/xbpm/V", 0.3, unit="mm")
    config = _single_plane_bpm_config()
    config["arrays"][0]["elements"] = ["XBPM"]
    sr = Accelerator.from_dict(config)
    bpms = sr.live.diagnostic.bpms.get("BPM")

    assert np.isnan(bpms.h.get()).all()
    assert np.allclose(bpms.v.get(), [0.3])
    assert bpms.positions.get().shape == (1, 2)
