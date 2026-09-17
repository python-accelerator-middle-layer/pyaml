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

    assert design.diagnostic.get("BETATRON_TUNE") is design.get_betatron_tune_monitor("BETATRON_TUNE")


def test_diagnostic_get_with_no_name_returns_all_configured_diagnostics():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    all_diagnostics = design.diagnostic.get()
    assert design.get_betatron_tune_monitor("BETATRON_TUNE") in all_diagnostics


def test_diagnostic_betatron_tune_returns_default_monitor():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    assert design.diagnostic.betatron_tune is design.get_betatron_tune_monitor("BETATRON_TUNE")


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
    design._DIAG["BETATRON_TUNE"] = design.orbit

    with pytest.raises(PyAMLException) as exc:
        _ = design.diagnostic.betatron_tune
    assert "BETATRON_TUNE" in str(exc.value)
    assert "BetatronTuneMonitor" in str(exc.value)
