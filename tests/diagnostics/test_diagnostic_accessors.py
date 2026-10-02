import copy

import pytest

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLException
from pyaml.lattice.simulator import Simulator


def test_diagnostic_get_returns_named_monitor():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    assert design.diagnostic.get("BETATRON_TUNE") is design._DIAG["BETATRON_TUNE"]


def test_diagnostic_get_with_no_name_returns_all_configured_diagnostics():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    all_diagnostics = design.diagnostic.get()
    assert design.diagnostic.get("BETATRON_TUNE") in all_diagnostics


def test_diagnostic_betatron_tune_returns_default_monitor():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    assert design.diagnostic.betatron_tune is design.diagnostic.get("BETATRON_TUNE")


def test_diagnostic_raises_when_default_missing(ebs_lattice_file):
    holder = Simulator(name="empty", lattice=str(ebs_lattice_file))

    with pytest.raises(PyAMLException) as exc:
        _ = holder.diagnostic.betatron_tune
    assert "BETATRON_TUNE" in str(exc.value)


def test_diagnostic_raises_when_default_wrong_type():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    # Swap the registered default so it points to an object of the wrong type.
    design._DIAG["BETATRON_TUNE"] = design.tool.orbit

    with pytest.raises(PyAMLException) as exc:
        _ = design.diagnostic.betatron_tune
    assert "BETATRON_TUNE" in str(exc.value)
    assert "BetatronTuneMonitor" in str(exc.value)


def test_diagnostic_bpm_returns_named_bpm():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    assert design.diagnostic.bpm.get("BPM_C04-04").get_name() == "BPM_C04-04"


def test_diagnostic_bpms_returns_named_array():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    bpms = design.diagnostic.bpms.get("BPM")
    assert design.diagnostic.bpm.get("BPM_C04-04") in bpms


def test_diagnostic_getitem_exact_name_matches_get():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    assert design.diagnostic["BETATRON_TUNE"] is design.diagnostic.get("BETATRON_TUNE")


def test_diagnostic_getitem_exact_name_miss_raises():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    with pytest.raises(PyAMLException):
        design.diagnostic["UNKNOWN"]


def test_diagnostic_getitem_wildcard_returns_an_array():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    matching = design.diagnostic["BETATRON*"]
    assert matching.names() == ["BETATRON_TUNE"]
    assert design.diagnostic["MISSING*"].names() == []


def test_diagnostic_getitem_list_selection_ignores_request_order():
    """A list-of-patterns selection lands in configuration order, whatever order the names
    were requested in, same as every other holder (see
    test_every_accessor_returns_a_list_selection_in_configuration_order). Only one diagnostic
    is registered by any existing fixture, so a distinct second entry is poked directly into
    the store (a renamed copy of the existing monitor) to make request order and
    configuration order observably different."""
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design
    spare_monitor = copy.copy(design.diagnostic.get("BETATRON_TUNE"))
    spare_monitor._name = "SPARE_BETATRON_TUNE"
    design._DIAG["SPARE_BETATRON_TUNE"] = spare_monitor

    forward = design.diagnostic[["BETATRON_TUNE", "SPARE_BETATRON_TUNE"]]
    backward = design.diagnostic[["SPARE_BETATRON_TUNE", "BETATRON_TUNE"]]
    assert forward.names() == backward.names() == ["BETATRON_TUNE", "SPARE_BETATRON_TUNE"]


def test_diagnostic_bpm_getitem_exact_name_matches_get():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    assert design.diagnostic.bpm["BPM_C04-04"] is design.diagnostic.bpm.get("BPM_C04-04")


def test_diagnostic_bpm_getitem_exact_name_miss_raises():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    with pytest.raises(PyAMLException):
        design.diagnostic.bpm["UNKNOWN"]


def test_diagnostic_bpm_getitem_wildcard_and_list_return_an_array():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    wildcard = design.diagnostic.bpm["BPM_C04-0[14]"]
    assert sorted(wildcard.names()) == ["BPM_C04-01", "BPM_C04-04"]

    listed = design.diagnostic.bpm[["BPM_C04-01", "BPM_C04-04"]]
    assert listed.names() == ["BPM_C04-01", "BPM_C04-04"]
