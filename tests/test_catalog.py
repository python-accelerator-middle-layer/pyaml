import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory


def _build_ro_attr(attribute: str, unit: str = "mm"):
    """
    Build a DeviceAccess prototype using the Factory (requires tango-pyaml in tests).
    """
    return Factory.build_object(
        {
            "type": "tango.pyaml.attribute_read_only",
            "attribute": attribute,
            "unit": unit,
        }
    )


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_view_get_one_and_identity_stability(install_test_package):
    """
    CatalogView.get_one() returns a stable DeviceAccessProxy.
    After a config update, the proxy identity must remain stable and only its target
    changes.
    """
    from tango.pyaml.attribute import Attribute
    from tango.pyaml.attribute import ConfigModel as AttrConfigModel

    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")

    cfg = sr.get_catalog(sr.live.get_catalog_name())
    view = cfg.view(sr.live)

    proxy_before = view.get_one("srdiag/bpm/c01-02/SA_HPosition")
    old_target = proxy_before.get_target()

    # Update the config catalog prototype (eager propagation to existing views)
    new_dev = Attribute(AttrConfigModel(attribute="srdiag/bpm/c01-02/SA_HPosition2"))
    cfg.update_proto("srdiag/bpm/c01-02/SA_HPosition", new_dev)

    proxy_after = view.get_one("srdiag/bpm/c01-02/SA_HPosition")

    assert proxy_after is proxy_before
    assert proxy_after.get_target() is not old_target
    assert proxy_after.get_target() is new_dev or proxy_after.get_target()._cfg.attribute.endswith("SA_HPosition2")


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_view_get_many_identity_stability(install_test_package):
    """
    For multi-device entries, CatalogView.get_many() returns a stable list of proxies.
    After a config update, proxy identities must remain stable and targets must change.
    """
    from tango.pyaml.attribute import Attribute
    from tango.pyaml.attribute import ConfigModel as AttrConfigModel

    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")

    cfg = sr.get_catalog(sr.live.get_catalog_name())
    view = cfg.view(sr.live)

    # We assume BPM_C01-02/x_pos and y_pos are single refs; for a true multi ref,
    # use a key that is configured as devices=[...]. If your config has none,
    # you can skip this test or add one reference in YAML.
    #
    # Here we validate multi-device behavior using a synthetic multi reference.
    devs1 = [
        _build_ro_attr("srdiag/bpm/c01-02/SA_HPosition"),
        _build_ro_attr("srdiag/bpm/c01-02/SA_VPosition"),
    ]
    cfg.add_proto("BPM_C01-02/positions", devs1)
    view.refresh_reference("BPM_C01-02/positions")

    proxies_before = view.get_many("BPM_C01-02/positions")
    targets_before = [p.get_target() for p in proxies_before]

    devs2 = [
        Attribute(AttrConfigModel(attribute="srdiag/bpm/c01-02/SA_HPosition2")),
        Attribute(AttrConfigModel(attribute="srdiag/bpm/c01-02/SA_VPosition2")),
    ]
    cfg.update_proto("BPM_C01-02/positions", devs2)

    proxies_after = view.get_many("BPM_C01-02/positions")
    targets_after = [p.get_target() for p in proxies_after]

    assert proxies_after == proxies_before
    assert targets_after != targets_before

    # targets_after should point to the new devices (or attached equivalent)
    assert targets_after[0]._cfg.attribute.endswith("SA_HPosition2")
    assert targets_after[1]._cfg.attribute.endswith("SA_VPosition2")


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_view_shape_stable_on_update(install_test_package):
    """
    Shape stability: a reference cannot change from single to multi (or multi to single)
    once the view has created proxies for it.
    """
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")

    cfg = sr.get_catalog(sr.live.get_catalog_name())
    view = cfg.view(sr.live)

    # Ensure existing single proxy
    _ = view.get_one("srdiag/bpm/c01-02/SA_HPosition")

    # Try to change the prototype to multi -> must raise at refresh time
    devs_multi = [
        _build_ro_attr("srdiag/bpm/c01-02/SA_HPosition"),
        _build_ro_attr("srdiag/bpm/c01-02/SA_VPosition"),
    ]
    with pytest.raises(PyAMLException, match="shape change is not supported"):
        cfg.update_proto("srdiag/bpm/c01-02/SA_HPosition", devs_multi)


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_view_sub_catalog_reuses_proxies(install_test_package):
    """
    Sub-catalogs must reuse the same proxy instances (no duplication).
    """
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")

    cfg = sr.get_catalog(sr.live.get_catalog_name())
    view = cfg.view(sr.live)

    p_parent = view.get_one("srdiag/bpm/c01-02/SA_HPosition")

    sub = view.get_sub_catalog(r"^srdiag/bpm/")
    p_sub = sub.get_one("srdiag/bpm/c01-02/SA_HPosition")

    assert p_sub is p_parent


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_view_sub_catalog_by_prefix_strips_prefix_and_reuses_proxies(
    install_test_package,
):
    """
    get_sub_catalog_by_prefix() must strip keys and reuse proxies.
    """
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")

    cfg = sr.get_catalog(sr.live.get_catalog_name())
    view = cfg.view(sr.live)

    p_parent = view.get_one("srdiag/bpm/c01-02/SA_HPosition")

    sub = view.get_sub_catalog_by_prefix("srdiag/bpm/c01-02/")
    assert sub.has_reference("SA_HPosition")

    p_sub = sub.get_one("SA_HPosition")
    assert p_sub is p_parent


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_config_catalog_update_propagates_to_existing_bpm_instance(
    install_test_package,
):
    """
    Integration test:
    Updating the config catalog must propagate to an already-created BPM object,
    via the CatalogView proxies used internally by the control system.
    """
    from tango.pyaml.attribute import Attribute
    from tango.pyaml.attribute import ConfigModel as AttrConfigModel

    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")

    # Create BPM first (it should have resolved proxies from the CS-bound view)
    bpm = sr.live.get_bpm("BPM_C01-02")

    cfg = sr.get_catalog(sr.live.get_catalog_name())
    liv_catalog_view = cfg.view(sr.live)  # ensure view exists and is registered for updates

    dev_x = Attribute(AttrConfigModel(attribute="srdiag/bpm/c01-02/SA_HPosition2"))
    dev_y = Attribute(AttrConfigModel(attribute="srdiag/bpm/c01-02/SA_VPosition2"))

    cfg.update_proto("srdiag/bpm/c01-02/SA_HPosition", dev_x)
    cfg.update_proto("srdiag/bpm/c01-02/SA_VPosition", dev_y)

    dev_x_live = liv_catalog_view.get_one("srdiag/bpm/c01-02/SA_HPosition")
    dev_y_live = liv_catalog_view.get_one("srdiag/bpm/c01-02/SA_VPosition")

    # The change is effective
    assert dev_x_live.name() == "srdiag/bpm/c01-02/SA_HPosition2"
    assert dev_y_live.name() == "srdiag/bpm/c01-02/SA_VPosition2"

    # Changing the values works on high-level objects.
    dev_x_live.set(1.0)
    dev_y_live.set(2.0)

    """
    With a real control system, the following code would have work but not on the dummy.
    dev_x.set(1.0)
    dev_y.set(2.0)
    """

    assert np.allclose(bpm.positions.get(), np.array([1.0, 2.0]))
