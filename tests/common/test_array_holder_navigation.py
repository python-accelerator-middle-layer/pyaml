import pytest

from pyaml.accelerator import Accelerator
from pyaml.arrays.bpm_array import BPMArray
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
    assert holder.magnet.HCORR is holder.magnet.get_array("HCORR")
    assert holder.magnet.VCORR is holder.magnet.get_array("VCORR")
    assert holder.magnet.HVCORR is holder.magnet.get_array("HVCORR")


def test_dynamic_attribute_returns_named_combined_function_magnet_array(holder):
    assert holder.combined_function_magnet.CFM is holder.combined_function_magnet.get_array("CFM")


def test_dynamic_attribute_returns_named_bpm_array(holder):
    assert holder.diagnostic.bpm.BPMS is holder.diagnostic.bpm.get_array("BPMS")


def test_dynamic_attribute_returns_named_array_of_serialized_families(serialized_holder):
    assert serialized_holder.magnet.QForTune is serialized_holder.magnet.get_array("QForTune")
    assert serialized_holder.magnet.series is serialized_holder.magnet.get_array("series")


def test_serialized_magnet_holder_shares_the_magnet_arrays(serialized_holder):
    assert serialized_holder.serialized_magnet.get_array("series") is serialized_holder.magnet.get_array("series")


def test_dynamic_attribute_unknown_name_raises_attribute_error(holder):
    with pytest.raises(AttributeError):
        _ = holder.magnet.UNKNOWN


def test_dynamic_attribute_does_not_shadow_existing_methods(holder):
    holder.magnet._array_store["get"] = holder.magnet.get_array("HCORR")
    holder.magnet._array_store["get_array"] = holder.magnet.get_array("HCORR")
    holder.magnet._array_store["add"] = holder.magnet.get_array("HCORR")

    assert callable(holder.magnet.get)
    assert callable(holder.magnet.get_array)
    assert callable(holder.magnet.add)
    assert holder.magnet.get_array("HCORR").names() == ["SH1A-C01-H", "SH1A-C02-H"]


def test_dynamic_attribute_rejects_non_identifier_names(holder):
    holder.magnet._array_store["not-an-id"] = holder.magnet.get_array("HCORR")

    with pytest.raises(AttributeError):
        getattr(holder.magnet, "not-an-id")


def test_dir_includes_configured_array_names(holder):
    assert {"HCORR", "VCORR", "HVCORR"} <= set(dir(holder.magnet))
    assert "CFM" in dir(holder.combined_function_magnet)
    assert "BPMS" in dir(holder.diagnostic.bpm)


def test_dir_excludes_non_identifier_array_names(holder):
    holder.magnet._array_store["not-an-id"] = holder.magnet.get_array("HCORR")

    assert "not-an-id" not in dir(holder.magnet)


def test_get_returns_one_element_and_get_array_returns_a_configured_array(holder):
    # get() looks up an element name and returns that element
    magnet = holder.magnet.get("SH1A-C01-H")
    assert magnet.get_name() == "SH1A-C01-H"

    # get_array() looks up an array name and returns the configured array
    correctors = holder.magnet.get_array("HCORR")
    assert type(correctors) is MagnetArray
    assert correctors.names() == ["SH1A-C01-H", "SH1A-C02-H"]


def test_element_names_and_array_names_live_in_separate_namespaces(holder):
    # An array name is not an element name
    with pytest.raises(PyAMLException):
        holder.magnet.get("HCORR")

    # An element name is not an array name
    with pytest.raises(PyAMLException):
        holder.magnet.get_array("SH1A-C01-H")


def test_get_array_without_name_returns_every_element_of_the_family(holder):
    # Each family holder returns its whole store, typed with the family array type
    magnets = holder.magnet.get_array()
    assert type(magnets) is MagnetArray
    assert magnets.names() == list(holder._MAGNETS)

    cfms = holder.combined_function_magnet.get_array()
    assert type(cfms) is CombinedFunctionMagnetArray
    assert cfms.names() == ["SH1A-C01", "SH1A-C02"]

    bpms = holder.diagnostic.bpm.get_array()
    assert type(bpms) is BPMArray
    assert bpms.names() == list(holder._BPMS)


def test_magnet_holder_navigation_on_a_real_lattice():
    sr = Accelerator.load("tests/config/EBSTune-patterns.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    # Configured family, by method and by attribute
    all_magnets = sr.design.magnet[:]
    quad_family = sr.design.magnet.get_array("QForTune")
    same_quad_family = sr.design.magnet.QForTune
    assert same_quad_family.names() == quad_family.names()
    assert len(quad_family) == 124
    assert len(all_magnets) >= len(quad_family)

    # No combined-function magnet in this lattice
    assert len(sr.design.combined_function_magnet.get_array()) == 0

    # A wildcard gives an array, a literal name gives the magnet itself
    matching_quadrupoles = sr.design.magnet["QF1*"]
    assert type(matching_quadrupoles) is MagnetArray
    one_magnet = sr.design.magnet["QF1E-C04"]
    assert one_magnet is sr.design.magnet.get("QF1E-C04")
    one_magnet.strength.set(0.8)
    assert one_magnet.strength.get() == pytest.approx(0.8)


def test_configured_exclusion_family_reproduced_with_selection_and_difference():
    """QForTest is QForTune minus a `~name`/`~pattern` YAML exclusion; `[]` and `-` reproduce it."""
    sr = Accelerator.load("tests/config/EBSTune-patterns.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    q_for_tune = sr.design.magnet.get_array("QForTune")
    q_for_test = sr.design.magnet.get_array("QForTest")  # QForTune, minus ~QF1E-C05 and ~Q???-C06

    reproduced = q_for_tune - sr.design.magnet[["QF1E-C05"]] - sr.design.magnet["Q???-C06"]

    assert reproduced == q_for_test


def test_configured_exclusion_family_reproduced_in_a_single_getitem_call():
    """The YAML `elements:` selector list (`[QD2*, QF1*, ~QF1E-C05, ~Q???-C06]`) selects the
    same *family* of elements through `[]` as declared for `QForTest`.

    Selection goes through the top-level holder, not `.magnet`, so it resolves patterns
    against the same global element pool `find_elements()`/`_fill_array` use to build
    `QForTest` in the YAML. The two therefore agree on *which* elements are selected, but not
    necessarily on their order: `_fill_array` concatenates matches pattern by pattern (all
    `QD2*` matches, then all `QF1*` matches) to build the named array, while `[]` (like every
    other list-selection accessor, see `test_every_accessor_returns_a_list_selection_in_configuration_order`)
    normalizes its result to configuration order regardless of how many patterns were
    involved or in what order they matched.
    """
    sr = Accelerator.load("tests/config/EBSTune-patterns.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    q_for_test = sr.design.magnet.get_array("QForTest")
    reproduced = sr.design[["QD2*", "QF1*", "~QF1E-C05", "~Q???-C06"]]

    assert type(reproduced) is type(q_for_test)
    assert set(reproduced.names()) == set(q_for_test.names())
    assert reproduced.names() == [n for n in sr.design.get_array().names() if n in set(q_for_test.names())]


def test_array_getitem_supports_a_negated_regex_pattern():
    """`~re:...` on an ElementArray excludes regex matches, same as `~wildcard`."""
    sr = Accelerator.load("tests/config/EBSTune-patterns.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()

    magnets = sr.design.magnet[:]
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

    qd2_family = sr.design.magnet.get_array("QD2Family")

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
    top-level holder, instead of falling back to a generic ElementArray."""
    wildcard = holder.magnet["SH1A-C0[12]-[HVQ]*"]
    assert type(wildcard) is MagnetArray


def test_magnet_holder_and_top_level_holder_getitem_agree_on_order(holder):
    """.magnet and the top-level holder (`[]` and `find_elements`) must return the same
    elements in the same order for the same name list, regardless of the order the names were
    requested in. The reference order is the configuration order, not the order of the
    requested names."""
    forward = holder.magnet[["SH1A-C01-H", "SH1A-C01-V"]]
    backward = holder.magnet[["SH1A-C01-V", "SH1A-C01-H"]]
    assert forward.names() == backward.names() == ["SH1A-C01-H", "SH1A-C01-V"]

    forward_top_level = holder[["SH1A-C01-H", "SH1A-C01-V"]]
    backward_top_level = holder[["SH1A-C01-V", "SH1A-C01-H"]]
    assert forward_top_level.names() == backward_top_level.names() == forward.names()

    assert holder.find_elements(["SH1A-C01-H", "SH1A-C01-V"]) == forward.names()
    assert holder.find_elements(["SH1A-C01-V", "SH1A-C01-H"]) == forward.names()


def test_combined_function_magnet_and_bpm_holders_return_list_selections_in_configuration_order(holder):
    """Every typed sub-holder must normalize list selections to configuration order, not just
    .magnet: this must also hold for .combined_function_magnet and .diagnostic.bpm."""
    cfm_forward = holder.combined_function_magnet[["SH1A-C01", "SH1A-C02"]]
    cfm_backward = holder.combined_function_magnet[["SH1A-C02", "SH1A-C01"]]
    assert cfm_forward.names() == cfm_backward.names() == ["SH1A-C01", "SH1A-C02"]

    bpm_forward = holder.diagnostic.bpm[["BPM_C04-01", "BPM_C04-02"]]
    bpm_backward = holder.diagnostic.bpm[["BPM_C04-02", "BPM_C04-01"]]
    assert bpm_forward.names() == bpm_backward.names() == ["BPM_C04-01", "BPM_C04-02"]


@pytest.mark.parametrize(
    "select",
    [
        pytest.param(lambda h, k: h[k].names(), id="holder[]"),
        pytest.param(lambda h, k: h.find_elements(k), id="holder.find_elements"),
        pytest.param(lambda h, k: h.get_array()[k].names(), id="holder.get_array()[]"),
        pytest.param(lambda h, k: h.magnet[k].names(), id="holder.magnet[]"),
        pytest.param(lambda h, k: h.magnet.get_array()[k].names(), id="holder.magnet.get_array()[]"),
    ],
)
@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reversed"])
@pytest.mark.parametrize(
    "key, expected_members",
    [
        pytest.param(
            ["SH1A-C01-H", "SH1A-C01-V", "SH1A-C02-H"],
            {"SH1A-C01-H", "SH1A-C01-V", "SH1A-C02-H"},
            id="literal-names",
        ),
        pytest.param(
            ["SH1A-C0?-H", "SH1A-C01-V"],
            {"SH1A-C01-H", "SH1A-C02-H", "SH1A-C01-V"},
            id="wildcard-and-literal",
        ),
    ],
)
def test_every_accessor_returns_a_list_selection_in_configuration_order(holder, select, reverse, key, expected_members):
    """Every name-based accessor must return a list-of-patterns selection in configuration
    order, whatever the order of the requested names/patterns, so that positional values line
    up the same way whichever accessor built the array. This must hold both for a list of
    literal names and for a list mixing a wildcard (matching several names) with a literal
    name, since a wildcard entry is where a naive pattern-order passthrough diverges from
    configuration order the most visibly."""
    expected = [n for n in holder.get_array().names() if n in expected_members]
    assert select(holder, key[::-1] if reverse else key) == expected


def test_subtracting_a_magnet_selection_from_a_mixed_selection_yields_a_cfm_array(holder):
    """A top-level selection mixing CombinedFunctionMagnet and their virtual correctors, minus
    the corrector-only .magnet selection, must yield the CFMs alone as a
    CombinedFunctionMagnetArray. Regression test: this used to raise 'Aggregator not
    implemented for CombinedFunctionMagnetArray' because the derived array blindly inherited
    the use_aggregator flag of the ElementArray it was built from."""
    mixed = holder["SH*"]
    only_magnets = holder.magnet["SH*"]
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
