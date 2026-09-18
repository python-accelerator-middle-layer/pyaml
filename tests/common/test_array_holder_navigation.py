import pytest

from pyaml.accelerator import Accelerator
from pyaml.arrays.cfm_magnet_array import CombinedFunctionMagnetArray


@pytest.fixture
def holder(accelerator_from_fragments, sr_configuration_fragments):
    sr = accelerator_from_fragments(*sr_configuration_fragments)
    sr.design.get_lattice().disable_6d()
    return sr.design


@pytest.fixture
def serialized_holder():
    sr = Accelerator.load("tests/config/sr_serialized_magnets.yaml", include_locations=False, ignore_external=True)
    return sr.design


def test_dynamic_attribute_returns_named_magnet_array(holder):
    assert holder.magnets.HCORR is holder.magnets.get("HCORR")
    assert holder.magnets.VCORR is holder.magnets.get("VCORR")
    assert holder.magnets.HVCORR is holder.magnets.get("HVCORR")


def test_dynamic_attribute_returns_named_combined_function_magnet_array(holder):
    assert holder.combined_function_magnets.CFM is holder.combined_function_magnets.get("CFM")


def test_dynamic_attribute_returns_named_bpm_array(holder):
    assert holder.diagnostic.bpms.BPMS is holder.diagnostic.bpms.get("BPMS")


def test_dynamic_attribute_returns_named_serialized_magnet_array(serialized_holder):
    assert serialized_holder.serialized_magnets.QForTune is serialized_holder.serialized_magnets.get("QForTune")
    assert serialized_holder.serialized_magnets.series is serialized_holder.serialized_magnets.get("series")


def test_dynamic_attribute_unknown_name_raises_attribute_error(holder):
    with pytest.raises(AttributeError):
        _ = holder.magnets.UNKNOWN


def test_dynamic_attribute_does_not_shadow_existing_methods(holder):
    holder.magnets._array_store["get"] = holder.magnets.get("HCORR")
    holder.magnets._array_store["add"] = holder.magnets.get("HCORR")

    assert callable(holder.magnets.get)
    assert callable(holder.magnets.add)
    assert holder.magnets.get("HCORR").names() == ["SH1A-C01-H", "SH1A-C02-H"]


def test_dynamic_attribute_rejects_non_identifier_names(holder):
    holder.magnets._array_store["not-an-id"] = holder.magnets.get("HCORR")

    with pytest.raises(AttributeError):
        getattr(holder.magnets, "not-an-id")


def test_dir_includes_configured_array_names(holder):
    assert {"HCORR", "VCORR", "HVCORR"} <= set(dir(holder.magnets))
    assert "CFM" in dir(holder.combined_function_magnets)
    assert "BPMS" in dir(holder.diagnostic.bpms)


def test_dir_excludes_non_identifier_array_names(holder):
    holder.magnets._array_store["not-an-id"] = holder.magnets.get("HCORR")

    assert "not-an-id" not in dir(holder.magnets)


def test_get_cfm_returns_all_combined_function_magnets(holder):
    combined_function_magnets = holder.magnets.get_cfm()

    assert type(combined_function_magnets) is CombinedFunctionMagnetArray
    assert combined_function_magnets.names() == holder.combined_function_magnets.get().names()


def test_issue_373_example():
    """Reproduce the #373 example verbatim, against real test lattice data."""
    sr = Accelerator.load("tests/config/EBSTune-patterns.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    all_magnets = sr.design.magnets[:]
    quad_family = sr.design.magnets.get("QForTune")
    same_quad_family = sr.design.magnets.QForTune
    assert same_quad_family.names() == quad_family.names()
    assert len(quad_family) == 124
    assert len(all_magnets) >= len(quad_family)

    combined_function_magnets = sr.design.magnets.get_cfm()
    assert len(combined_function_magnets) == 0

    matching_quadrupoles = sr.design.magnets["QF1*"]
    assert matching_quadrupoles.names() == sr.design.magnets["QF1*"].names()

    one_magnet = sr.design.magnet.get("QF1E-C04")
    one_magnet.strength.set(0.8)
    assert one_magnet.strength.get() == pytest.approx(0.8)
