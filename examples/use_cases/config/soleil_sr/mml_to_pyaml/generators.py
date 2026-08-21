"""
Generate pyAML YAML configuration files from parsed MML data.

Each ``generate_*`` function receives the dict returned by
:func:`mml_to_pyaml.parsers.load_mml_data` and returns a YAML string.
"""

import re

# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------


def _bpm_name(idx: int) -> str:
    return f"BPM_{idx:03d}"


def _cor_name(name: str) -> str:
    """``HCOR001`` → ``HCOR_001``, ``FHCOR02`` → ``FHCOR_002``, etc."""
    m = re.match(r"([A-Z]+)(\d+)", name)
    if m:
        return f"{m.group(1)}_{int(m.group(2)):03d}"
    return name


def _quad_name(family: str, idx: int) -> str:
    return f"{family}_{idx:03d}"


def _sext_name(name: str) -> str:
    return name.strip()


def _skewquad_name(name: str) -> str:
    return name.strip()


def _magnet_block(pyaml_type: str, name: str, powerconverter: str, unit: str = "A") -> list[str]:
    """Emit a single-multipole magnet entry with an identity model."""
    return [
        f"- type: {pyaml_type}",
        f"  name: {name}",
        "  model:",
        "    type: pyaml.magnet.identity_model",
        f"    unit: {unit}",
        f"    powerconverter: {powerconverter}",
    ]


# ---------------------------------------------------------------------------
# YAML generators
# ---------------------------------------------------------------------------


def generate_devices_yaml(data: dict) -> str:
    lines = []

    # BPMs — x_pos / y_pos are catalog keys (no model: wrapper)
    n = len(data["bpms"])
    lines.append(f"# --- BPMs ({n} devices) ---")
    for i, bpm in enumerate(data["bpms"], start=1):
        dev = bpm["device"]
        name = _bpm_name(i)
        lines += [
            "- type: pyaml.bpm.bpm",
            f"  name: {name}",
            f"  x_pos: {dev}/XPosSA",
            f"  y_pos: {dev}/ZPosSA",
        ]

    # Slow HCORs
    lines.append(f"# --- Slow Horizontal Correctors ({len(data['hcors'])} devices) ---")
    for hcor in data["hcors"]:
        lines += _magnet_block(
            "pyaml.magnet.hcorrector",
            _cor_name(hcor["name"]),
            f"{hcor['device']}/{hcor['attr_write']}",
        )

    # Slow VCORs
    lines.append(f"# --- Slow Vertical Correctors ({len(data['vcors'])} devices) ---")
    for vcor in data["vcors"]:
        lines += _magnet_block(
            "pyaml.magnet.vcorrector",
            _cor_name(vcor["name"]),
            f"{vcor['device']}/{vcor['attr_write']}",
        )

    # Fast HCORs
    lines.append(f"# --- Fast Horizontal Correctors ({len(data['fhcors'])} devices) ---")
    for fhcor in data["fhcors"]:
        lines += _magnet_block(
            "pyaml.magnet.hcorrector",
            _cor_name(fhcor["name"]),
            f"{fhcor['device']}/{fhcor['attr_write']}",
        )

    # Fast VCORs
    lines.append(f"# --- Fast Vertical Correctors ({len(data['fvcors'])} devices) ---")
    for fvcor in data["fvcors"]:
        lines += _magnet_block(
            "pyaml.magnet.vcorrector",
            _cor_name(fvcor["name"]),
            f"{fvcor['device']}/{fvcor['attr_write']}",
        )

    # Skew Quadrupoles (QT)
    lines.append(f"# --- Skew Quadrupoles ({len(data['skewquads'])} devices) ---")
    for qt in data["skewquads"]:
        lines += _magnet_block(
            "pyaml.magnet.skewquad",
            _skewquad_name(qt["name"]),
            f"{qt['device']}/currentPM",
        )

    # Quadrupoles Q1..Q12
    lines.append("# --- Quadrupoles (Q1..Q12) ---")
    for family, qlist in data["quads"].items():
        lines.append(f"# {family}")
        for i, q in enumerate(qlist, start=1):
            lines += _magnet_block(
                "pyaml.magnet.quadrupole",
                _quad_name(family, i),
                f"{q['device']}/currentPM",
            )

    # Sextupoles S1..S12 (one power supply each)
    lines.append("# --- Sextupoles (S1..S12, one power supply each) ---")
    for sext in data["sexts"]:
        lines += _magnet_block(
            "pyaml.magnet.sextupole",
            _sext_name(sext["name"]),
            f"{sext['device']}/currentPM",
        )

    # RF — masterclock is a catalog key string
    lines += [
        "# --- RF ---",
        "- type: pyaml.rf.rf_plant",
        "  name: RF",
        "  masterclock: ANS/RF/MasterClock/frequency",
    ]

    return "\n".join(lines) + "\n"


def generate_catalogs_yaml(data: dict) -> str:
    """Tango static catalog for BPM position attributes."""
    lines = [
        "- type: tango.pyaml.static_catalog",
        "  name: bpm-catalog",
        "  entries:",
    ]
    for _i, bpm in enumerate(data["bpms"], start=1):
        dev = bpm["device"]
        for attr in ("XPosSA", "ZPosSA"):
            full = f"{dev}/{attr}"
            lines += [
                "  - type: tango.pyaml.static_catalog_entry",
                f"    key: {full}",
                "    device:",
                "      type: tango.pyaml.attribute_read_only",
                f"      attribute: {full}",
                "      unit: mm",
            ]
    return "\n".join(lines) + "\n"


def generate_arrays_yaml(data: dict) -> str:
    lines = []

    # BPM array
    lines += ["- type: pyaml.arrays.bpm", "  name: BPM", "  elements:"]
    for i in range(1, len(data["bpms"]) + 1):
        lines.append(f"    - {_bpm_name(i)}")

    # Slow HCORR array → canonical name HCorr
    lines += ["- type: pyaml.arrays.magnet", "  name: HCorr", "  elements:"]
    for hcor in data["hcors"]:
        lines.append(f"    - {_cor_name(hcor['name'])}")

    # Slow VCORR array → canonical name VCorr
    lines += ["- type: pyaml.arrays.magnet", "  name: VCorr", "  elements:"]
    for vcor in data["vcors"]:
        lines.append(f"    - {_cor_name(vcor['name'])}")

    # Fast FHCORR array
    lines += ["- type: pyaml.arrays.magnet", "  name: FHCORR", "  elements:"]
    for fhcor in data["fhcors"]:
        lines.append(f"    - {_cor_name(fhcor['name'])}")

    # Fast FVCORR array
    lines += ["- type: pyaml.arrays.magnet", "  name: FVCORR", "  elements:"]
    for fvcor in data["fvcors"]:
        lines.append(f"    - {_cor_name(fvcor['name'])}")

    # Skew quadrupole array
    lines += ["- type: pyaml.arrays.magnet", "  name: SKEWQUAD", "  elements:"]
    for qt in data["skewquads"]:
        lines.append(f"    - {_skewquad_name(qt['name'])}")

    # Individual quad family arrays + combined QUAD array
    all_quads = []
    for family, qlist in data["quads"].items():
        arr_name = f"QUAD_{family}"
        lines += ["- type: pyaml.arrays.magnet", f"  name: {arr_name}", "  elements:"]
        for i, _q in enumerate(qlist, start=1):
            name = _quad_name(family, i)
            all_quads.append(name)
            lines.append(f"    - {name}")

    lines += ["- type: pyaml.arrays.magnet", "  name: QUAD", "  elements:"]
    for name in all_quads:
        lines.append(f"    - {name}")

    # Tune corrector array: families tagged 'Tune Corrector' in MML → canonical name QForTune
    tune_quad_families = data["roles"].get("Tune Corrector", [])
    lines += ["- type: pyaml.arrays.magnet", "  name: QForTune", "  elements:"]
    for family in tune_quad_families:
        if family in data["quads"]:
            for i in range(1, len(data["quads"][family]) + 1):
                lines.append(f"    - {_quad_name(family, i)}")

    # Sextupole array (all families)
    lines += ["- type: pyaml.arrays.magnet", "  name: SEXT", "  elements:"]
    for sext in data["sexts"]:
        lines.append(f"    - {_sext_name(sext['name'])}")

    # Chromaticity corrector array: families tagged 'Chromaticity Corrector' in MML → canonical name SextForChroma
    chroma_sext_families = set(data["roles"].get("Chromaticity Corrector", []))
    lines += ["- type: pyaml.arrays.magnet", "  name: SextForChroma", "  elements:"]
    for sext in data["sexts"]:
        if _sext_name(sext["name"]) in chroma_sext_families:
            lines.append(f"    - {_sext_name(sext['name'])}")

    return "\n".join(lines) + "\n"


TUNING_TOOLS_YAML = """\
# Tune monitor — tune_h / tune_v are catalog keys
- type: pyaml.diagnostics.tune_monitor
  name: BETATRON_TUNE
  tune_h: ANS/DG/TUNE/TuneH
  tune_v: ANS/DG/TUNE/TuneV
# Chromaticity monitor
- type: pyaml.tuning_tools.chromaticity_monitor
  name: CHROMATICITY_MONITOR
  betatron_tune_name: BETATRON_TUNE
  rf_plant_name: RF
  fit_order: 2
  n_avg_meas: 3
  n_step: 11
  sleep_between_meas: 2
  sleep_between_step: 2
  e_delta: 1e-3
  max_e_delta: 5e-3
# Tune correction (Q7 + Q9 via QForTune array)
- type: pyaml.tuning_tools.tune
  name: DEFAULT_TUNE_CORRECTION
  quad_array_name: QForTune
  betatron_tune_name: BETATRON_TUNE
  response_matrix: ${path:trm.json}
- type: pyaml.tuning_tools.tune_response_matrix
  name: DEFAULT_TUNE_RESPONSE_MATRIX
  quad_array_name: QForTune
  betatron_tune_name: BETATRON_TUNE
  quad_delta: 0.2
# Orbit correction (slow correctors)
- type: pyaml.tuning_tools.orbit_response_matrix
  bpm_array_name: BPM
  hcorr_array_name: HCorr
  vcorr_array_name: VCorr
  corrector_delta: 0.1
  name: DEFAULT_ORBIT_RESPONSE_MATRIX
- type: pyaml.tuning_tools.dispersion
  bpm_array_name: BPM
  rf_plant_name: RF
  frequency_delta: 100
  name: DEFAULT_DISPERSION
- type: pyaml.tuning_tools.orbit
  bpm_array_name: BPM
  hcorr_array_name: HCorr
  vcorr_array_name: VCorr
  name: DEFAULT_ORBIT_CORRECTION
  singular_values: 40
  response_matrix: ${path:orm.json}
"""

P_YAML = """\
type: pyaml.accelerator
facility: Synchrotron SOLEIL
machine: sr
data_folder: /data/store
energy: 2739100000.0
simulators:
- type: pyaml.lattice.simulator
  lattice: lat_superbend_rock_run4_2021.mat
  name: design
# controls:
# - type: tango.pyaml.controlsystem
#   name: live
#   tango_host: ans:20000
#   catalog: catalogs.yaml
# catalogs:
# - catalogs.yaml
arrays: arrays.yaml
devices:
- devices.yaml
- tuning_tools.yaml
"""
