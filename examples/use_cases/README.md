# Unified pyAML Examples

Three notebooks demonstrating tune correction, chromaticity measurement, and orbit correction. A single configuration variable at the top of each notebook selects the facility — the rest of the code runs unchanged.

## Notebooks

| Notebook | Topic |
|----------|-------|
| `01-tune_correction.ipynb` | Measure tune response matrix and correct betatron tune |
| `02-chromaticity_measurement.ipynb` | Measure chromaticity via RF frequency scan |
| `03-orbit_correction.ipynb` | Measure ORM and correct closed orbit |

## Facility configuration

Edit the `CONFIG_FILE` variable at the top of each notebook:

```python
CONFIG_FILE = "config/soleil_ii/p.yaml"   # SOLEIL II
# CONFIG_FILE = "config/bessy2/bessy2.yaml"  # BESSY2
# CONFIG_FILE = "config/esrf/esrf.yaml"      # ESRF EBS
```

## Installation

### SOLEIL II and ESRF (TANGO)

```bash
pip install accelerator-middle-layer[tango-pyaml]
```

### BESSY2 (EPICS)

```bash
pip install accelerator-middle-layer[pyaml-cs-oa]
```

To support both control systems in the same environment:

```bash
pip install accelerator-middle-layer[tango-pyaml,pyaml-cs-oa]
```

## Starting the virtual accelerator

### SOLEIL II

```bash
apptainer pull -F virtual-accelerator.sif oras://gitlab-registry.synchrotron-soleil.fr/software-control-system/containers/apptainer/virtual-accelerator:latest
apptainer run virtual-accelerator.sif
```

This starts the TANGO control system twin on `localhost:11000`.

### BESSY2

```bash
apptainer run oras://registry.hzdr.de/digital-twins-for-accelerators/containers/pyat-softioc-digital-twin:default-v0-5-1-bessy.2711893
```

> **BESSY2 PV prefix:** the virtual accelerator assigns a unique PV prefix (usually your username). Edit `config/bessy2/bessy2.yaml` and set `prefix:` under `controls:` to match:
> ```yaml
> controls:
>   - type: pyaml_cs_oa.controlsystem
>     prefix: "your_prefix:"   # ← change this
> ```

### ESRF EBS

Follow the ESRF internal documentation to start the EBS simulator and set `tango_host` in `config/esrf/esrf.yaml`.

## Control modes

Each notebook lets you choose between design and live mode:

```python
SR = sr.design   # simulation only — no control system needed
# SR = sr.live   # real machine or virtual twin
```

In `design` mode all wait times can be set to `0.0`. In `live` mode use `wait_time ≥ 1.5 s` to allow readbacks to settle.

## Named arrays and tools (canonical names used in all configs)

| Name | Description |
|------|-------------|
| `QForTune` | Quadrupoles for tune correction |
| `HCorr` | Horizontal orbit correctors |
| `VCorr` | Vertical orbit correctors |
| `BPM` | Beam position monitors |
| `BETATRON_TUNE` | Betatron tune monitor |
| `CHROMATICITY_MONITOR` | Chromaticity monitor |
| `DEFAULT_TUNE_CORRECTION` | Tune correction tool → `SR.tune` |
| `DEFAULT_TUNE_RESPONSE_MATRIX` | Tune response matrix tool → `SR.trm` |
| `DEFAULT_ORBIT_CORRECTION` | Orbit correction tool → `SR.orbit` |
| `DEFAULT_ORBIT_RESPONSE_MATRIX` | Orbit response matrix tool → `SR.orm` |
| `DEFAULT_DISPERSION` | Dispersion measurement tool → `SR.dispersion` |
