import pytest

from pyaml.accelerator import Accelerator
from pyaml.arrays.cfm_magnet_array import CombinedFunctionMagnetArray
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.common.exception import PyAMLException
from pyaml.configuration.manager import ConfigurationManager


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


def test_configured_exclusion_family_reproduced_with_selection_and_difference():
    """QForTest is QForTune minus a `~name`/`~pattern` YAML exclusion; `[]` and `-` reproduce it."""
    sr = Accelerator.load("tests/config/EBSTune-patterns.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    q_for_tune = sr.design.magnets.get("QForTune")
    q_for_test = sr.design.magnets.get("QForTest")  # QForTune, minus ~QF1E-C05 and ~Q???-C06

    reproduced = q_for_tune - sr.design.magnets["QF1E-C05"] - sr.design.magnets["Q???-C06"]

    assert reproduced == q_for_test


def test_configured_exclusion_family_reproduced_in_a_single_getitem_call():
    """The YAML `elements:` selector list (`[QD2*, QF1*, ~QF1E-C05, ~Q???-C06]`) works verbatim through `[]`.

    Selection goes through the top-level holder, not `.magnets`, so it resolves patterns
    against the same global element pool `find_elements()`/`_fill_array` use to build
    `QForTest` in the YAML, and so lands in the same order.
    """
    sr = Accelerator.load("tests/config/EBSTune-patterns.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    q_for_test = sr.design.magnets.get("QForTest")
    reproduced = sr.design[["QD2*", "QF1*", "~QF1E-C05", "~Q???-C06"]]

    assert type(reproduced) is type(q_for_test)
    assert reproduced == q_for_test


def test_array_getitem_supports_a_negated_regex_pattern():
    """`~re:...` on an ElementArray excludes regex matches, same as `~wildcard`."""
    sr = Accelerator.load("tests/config/EBSTune-patterns.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    magnets = sr.design.magnets[:]
    wildcard_exclusion = magnets["~QF1*"]
    regex_exclusion = magnets["~re:^QF1.*$"]

    assert len(regex_exclusion) > 0
    assert len(regex_exclusion) < len(magnets)
    assert regex_exclusion == wildcard_exclusion


def test_fill_array_supports_an_exclusion_outside_a_single_getitem_call_shape():
    """A YAML `elements:` list combining an inclusion and an exclusion builds an array, not a ValueError.

    `_fill_array` previously did its own include/exclude bookkeeping with `list.remove`,
    which raised whenever the excluded name wasn't already gathered by an inclusion
    pattern processed earlier in the same call. Delegating to `find_elements` (used here
    with the same list, for comparison) avoids that ordering trap.
    """
    manager = ConfigurationManager()
    manager.add("tests/config/EBSTune-patterns.yaml")
    manager.add({"arrays": [{"type": "pyaml.arrays.magnet", "name": "QD2Family", "elements": ["QD2*", "~QF1E-C05"]}]})
    sr = manager.build(ignore_external=True)
    sr.design.get_lattice().disable_6d()

    qd2_family = sr.design.magnets.get("QD2Family")

    assert qd2_family.names() == sr.design.find_elements(["QD2*", "~QF1E-C05"])


def test_magnet_holder_getitem_exact_name_matches_get(holder):
    assert holder.magnet["SH1A-C01-H"] is holder.magnet.get("SH1A-C01-H")


def test_magnet_holder_getitem_exact_name_miss_raises(holder):
    with pytest.raises(PyAMLException):
        holder.magnet["UNKNOWN"]


def test_magnet_holder_getitem_wildcard_and_list_return_an_array(holder):
    wildcard = holder.magnet["SH1A-C01-[HV]"]
    assert sorted(wildcard.names()) == ["SH1A-C01-H", "SH1A-C01-V"]
    assert holder.magnet["MISSING*"].names() == []

    listed = holder.magnet[["SH1A-C01-H", "SH1A-C01-V"]]
    assert listed.names() == ["SH1A-C01-H", "SH1A-C01-V"]


def test_magnet_holder_getitem_wildcard_returns_a_magnet_array(holder):
    """A wildcard restricted to the .magnet store is auto-typed as MagnetArray, like the
    top-level and .magnets holders, instead of falling back to a generic ElementArray."""
    wildcard = holder.magnet["SH1A-C0[12]-[HVQ]*"]
    assert type(wildcard) is MagnetArray


def test_magnet_and_magnets_holder_getitem_agree_on_order(holder):
    """.magnet (singular) and .magnets (plural) must return the same elements in the same
    order for the same name list, regardless of the order the names were requested in. The
    reference order is the configuration order, not the order of the requested names."""
    forward = holder.magnet[["SH1A-C01-H", "SH1A-C01-V"]]
    backward = holder.magnet[["SH1A-C01-V", "SH1A-C01-H"]]
    assert forward.names() == backward.names() == ["SH1A-C01-H", "SH1A-C01-V"]

    forward_plural = holder.magnets[["SH1A-C01-H", "SH1A-C01-V"]]
    backward_plural = holder.magnets[["SH1A-C01-V", "SH1A-C01-H"]]
    assert forward_plural.names() == backward_plural.names() == forward.names()


@pytest.mark.parametrize(
    "select",
    [
        pytest.param(lambda h, k: h[k].names(), id="holder[]"),
        pytest.param(lambda h, k: h.find_elements(k), id="holder.find_elements"),
        pytest.param(lambda h, k: h.get()[k].names(), id="holder.get()[]"),
        pytest.param(lambda h, k: h.magnet[k].names(), id="holder.magnet[]"),
        pytest.param(lambda h, k: h.magnets[k].names(), id="holder.magnets[]"),
    ],
)
@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reversed"])
def test_every_accessor_returns_a_list_selection_in_configuration_order(holder, select, reverse):
    """Every name-based accessor must return a list-of-patterns selection in configuration
    order, whatever the order of the requested names, so that positional values line up the
    same way whichever accessor built the array."""
    key = ["SH1A-C01-H", "SH1A-C01-V", "SH1A-C02-H"]
    expected = [n for n in holder.get().names() if n in key]
    assert select(holder, key[::-1] if reverse else key) == expected


def test_subtracting_a_magnet_selection_from_a_mixed_selection_yields_a_cfm_array(holder):
    """A top-level selection mixing CombinedFunctionMagnet and their virtual correctors, minus
    the corrector-only .magnets selection, must yield the CFMs alone as a
    CombinedFunctionMagnetArray. Regression test: this used to raise 'Aggregator not
    implemented for CombinedFunctionMagnetArray' because the derived array blindly inherited
    the use_aggregator flag of the ElementArray it was built from."""
    mixed = holder["SH*"]
    only_magnets = holder.magnets["SH*"]
    only_cfm = mixed - only_magnets

    assert type(only_cfm) is CombinedFunctionMagnetArray
    assert only_cfm.names() == ["SH1A-C01", "SH1A-C02"]


def test_magnet_holder_getitem_regex(holder):
    matching = holder.magnet["re:^SH1A-C0[12]-H$"]
    assert sorted(matching.names()) == ["SH1A-C01-H", "SH1A-C02-H"]


def test_combined_function_magnet_holder_getitem_exact_name_matches_get(holder):
    assert holder.combined_function_magnet["SH1A-C01"] is holder.combined_function_magnet.get("SH1A-C01")


def test_combined_function_magnet_holder_getitem_exact_name_miss_raises(holder):
    with pytest.raises(PyAMLException):
        holder.combined_function_magnet["UNKNOWN"]


def test_serialized_magnet_holder_getitem_exact_name_matches_get(serialized_holder):
    assert serialized_holder.serialized_magnet["mySeriesOfMagnets"] is serialized_holder.serialized_magnet.get(
        "mySeriesOfMagnets"
    )


def test_serialized_magnet_holder_getitem_exact_name_miss_raises(serialized_holder):
    with pytest.raises(PyAMLException):
        serialized_holder.serialized_magnet["UNKNOWN"]
