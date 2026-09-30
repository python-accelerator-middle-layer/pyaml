import pytest

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLException
from pyaml.lattice.simulator import Simulator


def test_tuning_tools_expose_configured_elements():
    sr = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    )
    design = sr.design

    tune_monitor = design.get_betatron_tune_monitor("BETATRON_TUNE")
    quadrupoles = design.magnets.get("QForTune")
    assert design.tool.tune.tune_monitor is tune_monitor
    assert design.tool.tune.quadrupoles is quadrupoles
    assert design.tool.trm.tune_monitor is tune_monitor
    assert design.tool.trm.quadrupoles is quadrupoles

    chromaticity_monitor = design.get_chromaticity_monitor("CHROMATICITY_MONITOR")
    sextupoles = design.magnets.get("Sext")
    assert design.tool.chromaticity.chromaticity_monitor is chromaticity_monitor
    assert design.tool.chromaticity.sextupoles is sextupoles
    assert design.tool.crm.chromaticity_monitor is chromaticity_monitor
    assert design.tool.crm.sextupoles is sextupoles

    bpms = design.diagnostic.bpms.get("BPM")
    rf_plant = design.rf.get("DEFAULT_RF_PLANT")
    assert chromaticity_monitor.tune_monitor is tune_monitor
    assert chromaticity_monitor.bpms is bpms
    assert chromaticity_monitor.rf_plant is rf_plant
    assert design.tool.dispersion.bpms is bpms
    assert design.tool.dispersion.rf_plant is rf_plant

    hcorrectors = design.magnets.get("HCorr")
    vcorrectors = design.magnets.get("VCorr")
    assert design.tool.orbit.bpms is bpms
    assert design.tool.orbit.hcorrectors is hcorrectors
    assert design.tool.orbit.vcorrectors is vcorrectors
    assert design.tool.orbit.correctors.names() == hcorrectors.names() + vcorrectors.names()
    assert design.tool.orbit.rf_plant is rf_plant
    assert design.tool.orm.bpms is bpms
    assert design.tool.orm.hcorrectors is hcorrectors
    assert design.tool.orm.vcorrectors is vcorrectors

    for name in ("BBA-BPM_C04-04", "BBA2-BPM_C04-04"):
        bba = design.get_bba(name)
        assert bba.bpms is bpms
        assert bba.bpm is design.diagnostic.bpm.get("BPM_C04-04")
        assert bba.hcorrector is design.magnet.get("SF2E-C02-H")
        assert bba.vcorrector is design.magnet.get("SD1A-C26-V")
        assert bba.quadrupole is design.magnet.get("QF6B-C04")

    assert design.get_bba("BBA2-BPM_C04-04").tune_correction is design.tool.tune


def test_tool_get_returns_named_tool():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    assert design.tool.get("DEFAULT_TUNE_CORRECTION") is design.tool.tune
    assert design.tool.get("DEFAULT_ORBIT_RESPONSE_MATRIX") is design.tool.orm


def test_tool_get_with_no_name_returns_all_configured_tools():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    all_tools = design.tool.get()
    assert design.tool.tune in all_tools
    assert design.tool.trm in all_tools
    assert design.tool.orbit in all_tools
    assert design.tool.orm in all_tools
    assert design.tool.chromaticity in all_tools
    assert design.tool.crm in all_tools
    assert design.tool.dispersion in all_tools


def test_tool_raises_when_default_missing(ebs_lattice_file):
    holder = Simulator(name="empty", lattice=str(ebs_lattice_file))

    with pytest.raises(PyAMLException) as exc:
        _ = holder.tool.tune
    assert "DEFAULT_TUNE_CORRECTION" in str(exc.value)


def test_tool_raises_when_default_wrong_type():
    design = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    ).design

    # Swap the registered default so it points to an object of the wrong type.
    design._TOOLS["DEFAULT_TUNE_CORRECTION"] = design.tool.orbit

    with pytest.raises(PyAMLException) as exc:
        _ = design.tool.tune
    assert "DEFAULT_TUNE_CORRECTION" in str(exc.value)
    assert "Tune" in str(exc.value)
