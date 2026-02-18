import pytest

from pyaml import PyAMLException
from pyaml.configuration.catalog import Catalog
from pyaml.configuration.catalog import ConfigModel as CatalogConfigModel
from pyaml.configuration.catalog_entry import (
    CatalogEntry,
)
from pyaml.configuration.catalog_entry import (
    ConfigModel as CatalogEntryConfigModel,
)
from pyaml.configuration.factory import Factory


def _build_ro_attr(attribute: str, unit: str = "mm"):
    """Build a DeviceAccess using the Factory (requires tango-pyaml in tests)."""
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
def test_catalog_entry_requires_exactly_one_of_device_or_devices(install_test_package):
    dev = _build_ro_attr("srdiag/bpm/c04-01/SA_HPosition")

    # neither device nor devices
    with pytest.raises(ValueError, match="exactly one of 'device' or 'devices'"):
        CatalogEntryConfigModel(reference="k1")

    # both device and devices
    with pytest.raises(ValueError, match="exactly one of 'device' or 'devices'"):
        CatalogEntryConfigModel(reference="k1", device=dev, devices=[dev])

    # devices is empty -> treated as "not provided" => invalid
    with pytest.raises(ValueError, match="exactly one of 'device' or 'devices'"):
        CatalogEntryConfigModel(reference="k1", devices=[])


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_config_model_rejects_duplicate_references(install_test_package):
    dev1 = _build_ro_attr("srdiag/bpm/c04-01/SA_HPosition")
    dev2 = _build_ro_attr("srdiag/bpm/c04-01/SA_VPosition")

    e1 = CatalogEntry(CatalogEntryConfigModel(reference="BPM/x_pos", device=dev1))
    e2 = CatalogEntry(CatalogEntryConfigModel(reference="BPM/x_pos", device=dev2))

    with pytest.raises(ValueError, match="Duplicate catalog reference"):
        CatalogConfigModel(name="live_catalog", refs=[e1, e2])


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_get_get_one_get_many(install_test_package):
    dev = _build_ro_attr("srdiag/bpm/c04-01/SA_HPosition")
    entry = CatalogEntry(
        CatalogEntryConfigModel(reference="BPM_C04-01/x_pos", device=dev)
    )
    cat = Catalog(CatalogConfigModel(name="live_catalog", refs=[entry]))

    # get / get_one on a single-device entry
    assert cat.get("BPM_C04-01/x_pos") is dev
    assert cat.get_one("BPM_C04-01/x_pos") is dev

    # get_many on a single-device entry -> error
    with pytest.raises(PyAMLException, match="is single-device; use get_one"):
        cat.get_many("BPM_C04-01/x_pos")

    # missing reference -> error
    with pytest.raises(PyAMLException, match="not found"):
        cat.get("does/not/exist")


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_multi_device_get_many_and_get_one_error(install_test_package):
    dev1 = _build_ro_attr("srdiag/bpm/c04-01/SA_HPosition")
    dev2 = _build_ro_attr("srdiag/bpm/c04-01/SA_VPosition")

    entry = CatalogEntry(
        CatalogEntryConfigModel(reference="BPM_C04-01/positions", devices=[dev1, dev2])
    )
    cat = Catalog(CatalogConfigModel(name="live_catalog", refs=[entry]))

    many = cat.get_many("BPM_C04-01/positions")
    assert many == [dev1, dev2]

    # get_one on a multi-device entry -> error
    with pytest.raises(PyAMLException, match="is multi-device; use get_many"):
        cat.get_one("BPM_C04-01/positions")


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_find_and_find_by_prefix(install_test_package):
    devx1 = _build_ro_attr("srdiag/bpm/c04-01/SA_HPosition")
    devy1 = _build_ro_attr("srdiag/bpm/c04-01/SA_VPosition")
    devx2 = _build_ro_attr("srdiag/bpm/c04-02/SA_HPosition")

    cat = Catalog(
        CatalogConfigModel(
            name="live_catalog",
            refs=[
                CatalogEntry(
                    CatalogEntryConfigModel(reference="BPM_C04-01/x_pos", device=devx1)
                ),
                CatalogEntry(
                    CatalogEntryConfigModel(reference="BPM_C04-01/y_pos", device=devy1)
                ),
                CatalogEntry(
                    CatalogEntryConfigModel(reference="BPM_C04-02/x_pos", device=devx2)
                ),
            ],
        )
    )

    # regex search
    res = cat.find(r"BPM_C04-01/.*_pos$")
    assert set(res.keys()) == {"BPM_C04-01/x_pos", "BPM_C04-01/y_pos"}

    # prefix search (literal prefix escaped internally)
    res2 = cat.find_by_prefix("BPM_C04-01/")
    assert set(res2.keys()) == {"BPM_C04-01/x_pos", "BPM_C04-01/y_pos"}


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_get_sub_catalog_regex(install_test_package):
    devx1 = _build_ro_attr("srdiag/bpm/c04-01/SA_HPosition")
    devy1 = _build_ro_attr("srdiag/bpm/c04-01/SA_VPosition")
    devx2 = _build_ro_attr("srdiag/bpm/c04-02/SA_HPosition")

    cat = Catalog(
        CatalogConfigModel(
            name="live_catalog",
            refs=[
                CatalogEntry(
                    CatalogEntryConfigModel(reference="BPM_C04-01/x_pos", device=devx1)
                ),
                CatalogEntry(
                    CatalogEntryConfigModel(reference="BPM_C04-01/y_pos", device=devy1)
                ),
                CatalogEntry(
                    CatalogEntryConfigModel(reference="BPM_C04-02/x_pos", device=devx2)
                ),
            ],
        )
    )

    sub = cat.get_sub_catalog(r"^BPM_C04-01/")
    assert set(sub.keys()) == {"BPM_C04-01/x_pos", "BPM_C04-01/y_pos"}
    assert sub.get_one("BPM_C04-01/x_pos") is devx1


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_get_sub_catalog_by_prefix_strips_prefix(install_test_package):
    devx1 = _build_ro_attr("srdiag/bpm/c04-01/SA_HPosition")
    devy1 = _build_ro_attr("srdiag/bpm/c04-01/SA_VPosition")

    cat = Catalog(
        CatalogConfigModel(
            name="live_catalog",
            refs=[
                CatalogEntry(
                    CatalogEntryConfigModel(reference="BPM_C04-01/x_pos", device=devx1)
                ),
                CatalogEntry(
                    CatalogEntryConfigModel(reference="BPM_C04-01/y_pos", device=devy1)
                ),
            ],
        )
    )

    sub = cat.get_sub_catalog_by_prefix("BPM_C04-01/")
    # Prefix must be removed in the returned catalog
    assert set(sub.keys()) == {"x_pos", "y_pos"}
    assert sub.get_one("x_pos") is devx1
    assert sub.get_one("y_pos") is devy1

    # Removing the full key must fail (would produce an empty key)
    with pytest.raises(PyAMLException, match="results in an empty reference"):
        cat.get_sub_catalog_by_prefix("BPM_C04-01/x_pos")


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_catalog_has_reference(install_test_package):
    dev = _build_ro_attr("srdiag/bpm/c04-01/SA_HPosition")
    cat = Catalog(
        CatalogConfigModel(
            name="live_catalog",
            refs=[
                CatalogEntry(
                    CatalogEntryConfigModel(reference="BPM_C04-01/x_pos", device=dev)
                ),
            ],
        )
    )

    assert cat.has_reference("BPM_C04-01/x_pos") is True
    assert cat.has_reference("BPM_C04-01/y_pos") is False
