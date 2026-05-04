# Changelog

All notable changes to this project will be documented in this file.

## [0.2.5]

### Added
- **Automatic versioning** via `hatch-vcs`: `__version__` is now generated automatically from git tags on install (`pyaml/_version.py`)
- **`ConfigurationManager`**: new class for incremental accelerator configuration with explicit build flow; supports REST as a configuration source
- **YellowPages**: standardized element name mapping and discovery with preserved element order and updated query syntax
- **Wildcards and regex** support in array definitions in YAML configuration files (exclusion pattern `~`)
- **Python-based configuration macros** using the `elements_code` key
- **`CfgDict` class**: allows plain Python dicts in pydantic-based configuration
- **RF-orbit correction** capabilities including RF frequency correction and weight handling
- **Chromaticity tool** and **tune monitor interface** (frequency-based)
- **`TuningTool` and `MeasurementTool`** abstract base classes
- **`OrbitResponseMatrixData`** and unified Tune/Orbit response matrix tools
- **External tune monitor** support
- **Shared Tango attribute state** in the dummy control system
- **SOLEIL II examples** including orbit correction in DESIGN mode
- **OphydDevice example** added
- Ctrl+C handling for aborting tuning tools and restoring initial state
- `add_device()` method and object creation from class for unbound elements
- Dispersion fit flag and dispersion plot in orbit tools

### Changed
- Response matrix tools unified and renamed (`ResponseMatrixData`, `variable_*` / `observable_*` instead of `input_*` / `output_*`)
- `get_peer()` renamed to `get_peer_name()` for clarity
- Peer added to `ElementHolder`; private peer access cleaned up via public property
- Factory custom strategy removed (simplified API)
- Ruff line length increased to 127; code reformatted accordingly

### Fixed
- Four `AttributeError` bugs in `LinearSerializedMagnetModel` (wrong field names, misplaced attribute access)
- Serialized magnets: correct sub-magnet list, strength computation, and combined-function magnet handling
- YAML list expansion bug
- Error reporting in factory
- `UnboundElement` validation
- `get_devices` broken for serialized magnets (#253)
- Regression in configuration errors with line number reporting
- Various ESRF, BESSY2 example and test fixes

## [0.2.4]

<!-- Add notes for previous releases here -->
