## Description

Add named `Catalog` objects to the PyAML configuration so device references can be resolved by key at control-system attachment time.

This is a major cross-cutting change. It must stay conceptually minimal, but it affects the full PyAML object model because any object configuration that currently carries `DeviceAccess` instances may now carry catalog keys instead.

A catalog is only responsible for resolving a string key into a `DeviceAccess`. PyAML must provide a built-in catalog manager based on an explicit `key -> DeviceAccess` mapping. Catalogs may therefore be static or dynamic:

- the built-in static catalog manager stores explicit `key -> DeviceAccess` entries;
- a dynamic catalog can reconstruct the `DeviceAccess` from the key alone, possibly by querying an external system.

When a catalog is attached to a control system, the control system must notify the catalog of that attachment. This lifecycle notification is especially important for dynamic catalogs, which may need the control-system context to resolve keys correctly.

Example: a project such as `tango-pyaml`, which already provides the Tango control-system integration, may expose a dedicated dynamic catalog implementation that queries the Tango database and builds the proper `DeviceAccess` from the requested key.

Control systems must be able to use:

- a single named catalog declared at accelerator level;
- or a single inline catalog declared directly inside the control-system configuration for convenience.

The same catalog object may be referenced and shared by several control systems.

This document is intentionally written so it can be used as an implementation prompt. The implementation must follow the scope and non-goals below.

## Related Issue

This project only accepts pull requests related to open issues. If suggesting a new feature or change, please discuss it in an issue first.

- Fixes #187

Features/issues described there are:
- [ ] new feature: introduce top-level named catalogs in `pyaml.accelerator.ConfigModel`, because device resolution must be configurable independently from the element models.
- [ ] new feature: define a minimal catalog abstraction whose only required responsibility is `resolve(key) -> DeviceAccess`, because dynamic catalogs must not be forced to enumerate all valid keys.
- [ ] new feature: provide a built-in PyAML catalog manager backed by an explicit `key -> DeviceAccess` mapping, because a standard static implementation must exist without requiring an external plugin.
- [ ] new feature: allow a `ControlSystem` to declare `catalog: str | Catalog | None`, because each control system must use exactly one catalog, either by named reference or inline declaration.
- [ ] new feature: define a catalog attachment notification from `ControlSystem` to `Catalog`, because dynamic catalogs may require control-system-specific context before resolving keys.
- [ ] new feature: allow configuration fields across PyAML that currently store `DeviceAccess` objects to also accept string keys, because the actual device may now come from a catalog.
- [ ] new feature: support external catalog implementations loaded through the existing factory mechanism, because dynamic catalogs may require specialized logic such as reconstructing Tango `DeviceAccess` objects from an attribute key.

## Scope and Non-Goals

The implementation must stay within the following scope:

- [ ] catalogs only resolve keys to `DeviceAccess`;
- [ ] catalog resolution happens lazily, when a `ControlSystem` is about to call `attach()` or `attach_array()`;
- [ ] existing configurations that provide direct `DeviceAccess` objects must keep working unchanged;
- [ ] the implementation must be applied consistently across PyAML objects, not only BPM-related classes.

The following ideas are explicitly out of scope and must not be introduced:

- [ ] no `CatalogView`;
- [ ] no `DeviceAccessProxy`;
- [ ] no sub-catalog or filtered catalog API;
- [ ] no `keys()` requirement on catalogs;
- [ ] no runtime propagation of catalog updates into already attached objects;
- [ ] no BPM-specific redesign just to support catalogs;
- [ ] no assumption that every catalog can enumerate or validate all possible keys ahead of time.

## Expected Design

Use the existing code structure and keep the change localized.

- [ ] add a minimal catalog interface or base class under `pyaml.configuration` with an API centered on `resolve(key: str) -> DeviceAccess`;
- [ ] provide a built-in PyAML catalog manager for explicit config-defined `key -> DeviceAccess` entries;
- [ ] make `Catalog.name` part of the catalog object itself, so top-level catalogs are referenced by their own declared name;
- [ ] add a catalog lifecycle hook so a catalog can be notified when it is attached to a `ControlSystem`;
- [ ] extend `Accelerator.ConfigModel` with `catalogs: list[Catalog] | None`;
- [ ] keep a registry of named catalogs in `Accelerator`, with a small public accessor such as `get_catalog(name: str)`;
- [ ] extend control-system configuration so a control system can declare `catalog: str | Catalog | None`;
- [ ] resolve those catalog references during accelerator initialization, before `fill_device()` is called;
- [ ] inject the resolved catalog object into each control system;
- [ ] notify the catalog from the control system once the catalog is attached to it;
- [ ] add a small utility in `ControlSystem` to convert `DeviceAccess | str | None` into `DeviceAccess | None`;
- [ ] use that utility immediately before each `attach()` and `attach_array()` call instead of changing the attachment model itself.

## Changes to existing functionality

Describe the changes that had to be made to an existing functionality (if they were made)

- [ ] `Accelerator` must now build and store named catalogs before attaching devices to control systems, because control systems may resolve string keys through one configured catalog, either by name or inline object.
- [ ] `ControlSystem` must notify its attached catalog of the attachment event, because dynamic catalogs may require the control-system context before `resolve()` is used.
- [ ] `ControlSystem.fill_device()` and related aggregation paths must resolve string keys into `DeviceAccess` objects before calling `attach()` / `attach_array()`, because models may now carry either an actual device or a catalog key.
- [ ] configuration models across PyAML that currently type device fields as `DeviceAccess` must be updated to accept `DeviceAccess | str`, while preserving their existing APIs as much as possible.
- [ ] direct `DeviceAccess` configuration remains supported and must not require a catalog.
- [ ] the built-in PyAML catalog manager becomes the default static catalog implementation used for named and inline mapping-based catalogs.
- [ ] error handling must stay explicit: unknown named catalog, missing resolver on a control system, or unresolved key must raise clear `PyAMLException` / `PyAMLConfigException` messages.

## Implementation Notes

Use these constraints when implementing:

- [ ] prefer minimal API additions over broad refactors;
- [ ] keep the notion of catalog attached to the control-system side, not to BPM-specific runtime helpers;
- [ ] do not add any API that implies catalogs are enumerable;
- [ ] a control system stores at most one resolved catalog reference;
- [ ] if no catalog resolves a key, raise a clear error mentioning the key and the control-system name when available;
- [ ] if a control system references a named catalog, resolve it once during accelerator initialization and reuse that same catalog object;
- [ ] it must be possible for several control systems to reference the same catalog object;
- [ ] if the same catalog object is shared by several control systems, the catalog attachment notification API must support that lifecycle cleanly;
- [ ] if duplicate catalog names are declared at accelerator level, fail fast during accelerator construction;
- [ ] if a static catalog contains duplicate explicit keys, fail fast during its validation;
- [ ] the built-in catalog manager should remain simple: explicit mapping storage plus `resolve(key)`, without any catalog-view or synchronization behavior;
- [ ] keep external dynamic catalogs pluggable through `type`-based factory loading;
- [ ] document and preserve the extension path for external providers such as `tango-pyaml`, which may use their own control-system metadata source to reconstruct `DeviceAccess` objects dynamically;
- [ ] treat this as a project-wide typing and attachment change, and review all PyAML object families for `DeviceAccess`-typed config fields and attachment flows.

Recommended areas to update:

- [ ] `pyaml/accelerator.py`
- [ ] `pyaml/control/controlsystem.py`
- [ ] new catalog modules under `pyaml/configuration/`
- [ ] all config models and attachment paths that currently accept or manipulate `DeviceAccess`, including BPMs, magnets, serialized magnets, RF, tune monitors, arrays, tools, and any external object integrated through the standard PyAML construction flow

## Impacted PyAML Objects

The implementation must be reviewed against the following PyAML object families.

Directly impacted objects and models:

- [ ] `Accelerator`
- [ ] `ControlSystem`
- [ ] `BPMModel`
- [ ] `BPMSimpleModel`
- [ ] `BPMTiltOffsetModel`
- [ ] `BetatronTuneMonitor`
- [ ] `MagnetModel`
- [ ] `IdentityMagnetModel`
- [ ] `IdentityCFMagnetModel`
- [ ] `LinearMagnetModel`
- [ ] `LinearCFMagnetModel`
- [ ] `LinearSerializedMagnetModel`
- [ ] `SplineMagnetModel`
- [ ] `RFPlant`
- [ ] `RFTransmitter`

Indirectly impacted runtime objects and attachment paths:

- [ ] `BPM`
- [ ] `Magnet`
- [ ] `CombinedFunctionMagnet`
- [ ] `SerializedMagnets`
- [ ] control-system magnet aggregators
- [ ] control-system BPM aggregators
- [ ] control-system RF attachment flow
- [ ] control-system tune-monitor attachment flow
- [ ] any external object built through the standard PyAML factory flow whose config contains `DeviceAccess` fields

Objects not expected to require direct catalog-aware config changes, but that must still be checked for regressions:

- [ ] `Simulator`
- [ ] arrays built on top of already attached objects
- [ ] `TuningTool`
- [ ] `MeasurementTool`
- [ ] `YellowPages`

## Configuration Examples

The examples below illustrate the intended configuration style.

Top-level static catalogs provided by base PyAML:

```yaml
type: pyaml.accelerator
facility: SOLEIL
machine: StorageRing
energy: 2.75e9
data_folder: .

catalogs:
  - type: pyaml.configuration.static_catalog
    name: bpm-common
    refs:
      BPM_C01-01/x:
        type: tango.pyaml.attribute_read_only
        attribute: srdiag/bpm/c01-01/XPosSA
        unit: mm
      BPM_C01-01/y:
        type: tango.pyaml.attribute_read_only
        attribute: srdiag/bpm/c01-01/YPosSA
        unit: mm
      BPM_C01-01/tilt:
        type: tango.pyaml.attribute_read_only
        attribute: srdiag/bpm/c01-01/Tilt
        unit: rad
```

Control system using a named shared catalog:

```yaml
controls:
  - type: tango.pyaml.controlsystem
    name: live
    catalog: bpm-common

  - type: tango.pyaml.controlsystem
    name: ops
    catalog: bpm-common
```

Objects using catalog keys instead of direct `DeviceAccess` declarations:

```yaml
devices:
  - type: pyaml.bpm.bpm
    name: BPM_C01-01
    model:
      type: pyaml.bpm.bpm_tiltoffset_model
      x_pos: BPM_C01-01/x
      y_pos: BPM_C01-01/y
      tilt: BPM_C01-01/tilt

  - type: pyaml.diagnostics.tune_monitor
    name: tune
    tune_h: tune/h
    tune_v: tune/v
```

Combined-function magnet example using catalog keys for power converters:

```yaml
devices:
  - type: pyaml.magnet.cfm_magnet
    name: SH1A-C01
    mapping:
      - [B0, SH1A-C01-H]
      - [A0, SH1A-C01-V]
      - [A1, SH1A-C01-SQ]
    model:
      type: pyaml.magnet.linear_cfm_model
      multipoles: [B0, A0, A1]
      units: [rad, rad, m-1]
      pseudo_factors: [1.0, -1.0, -1.0]
      curves:
        - type: pyaml.configuration.csvcurve
          file: sr/magnet_models/SH1_SH3_h_strength.csv
        - type: pyaml.configuration.csvcurve
          file: sr/magnet_models/SH1_SH3_v_strength.csv
        - type: pyaml.configuration.csvcurve
          file: sr/magnet_models/SH1_SH3_sq_strength.csv
      matrix:
        type: pyaml.configuration.csvmatrix
        file: sr/magnet_models/SH_matrix.csv
      powerconverters:
        - SH1A-C01/ps1
        - SH1A-C01/ps2
        - SH1A-C01/ps3
```

With matching static catalog entries:

```yaml
catalogs:
  - type: pyaml.configuration.static_catalog
    name: correctors
    refs:
      SH1A-C01/ps1:
        type: tango.pyaml.attribute
        attribute: srmag/ps-corr-sh1/c01-a-ch1/current
        unit: A
      SH1A-C01/ps2:
        type: tango.pyaml.attribute
        attribute: srmag/ps-corr-sh1/c01-a-ch2/current
        unit: A
      SH1A-C01/ps3:
        type: tango.pyaml.attribute
        attribute: srmag/ps-corr-sh1/c01-a-ch3/current
        unit: A
```

Dynamic external catalog example with `tango-pyaml`:

```yaml
catalogs:
  - type: tango.pyaml.attribute_catalog
    name: tango-db
    domain: SR
    family: BPM
```

In this case, the catalog does not need to declare all keys explicitly. It may reconstruct the proper `DeviceAccess` on demand by querying the Tango database from the requested key.

Control system using an inline catalog:

```yaml
controls:
  - type: tango.pyaml.controlsystem
    name: live
    catalog:
      type: pyaml.configuration.static_catalog
      name: live-local
      refs:
        tune/h:
          type: tango.pyaml.attribute_read_only
          attribute: srdiag/tune/X
          unit: ""
        tune/v:
          type: tango.pyaml.attribute_read_only
          attribute: srdiag/tune/Z
          unit: ""
```

Control system using a dynamic external catalog:

```yaml
controls:
  - type: tango.pyaml.controlsystem
    name: live
    catalog: tango-db
```

## Testing
 The following tests (compatible with pytest) should be added:
 - [ ] load an accelerator with top-level named catalogs and resolve a device key from a control system
 - [ ] share one named catalog between several control systems and verify they reference the same catalog object
 - [ ] load a control system with an inline catalog and resolve a device key
 - [ ] keep existing behavior when a config provides direct `DeviceAccess` objects instead of keys
 - [ ] fail clearly on unknown catalog name referenced by a control system
 - [ ] fail clearly on unresolved key
 - [ ] fail clearly on duplicate top-level catalog names
 - [ ] fail clearly on duplicate keys inside a static catalog
 - [ ] validate at least one dynamic catalog fixture that reconstructs a `DeviceAccess` from a key without a predeclared entry list

## Verify that your checklist complies with the project
- [ ] New and existing unit tests pass locally
- [ ] Tests were added to prove that all features/changes are effective
- [ ] The code is commented where appropriate
- [ ] Any existing features are not broken (unless there is an explicit change to an existing functionality)
