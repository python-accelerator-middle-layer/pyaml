# Add dt4acc Apptainer Integration Smoke Test

## Description, motivation and use case

pyAML currently has unit tests for its core configuration and backend
abstractions, but it does not have an integration test proving that a real
Tango-backed digital twin can be started and consumed through the pyAML API.

The use case is to validate the integration between:

- pyAML `Accelerator` configuration loading;
- `tango-pyaml` as the Tango backend;
- the `dt4acc` SOLEIL twin running in Apptainer with its embedded Tango
  database.

A minimal first test should ensure that the dt4acc twin starts successfully,
that Tango devices are reachable, and that pyAML can instantiate an
`Accelerator` and read at least one live value from the twin.

## Proposed solution

Add an opt-in GitHub Actions integration workflow that:

1. Installs Apptainer.
2. Pulls the `dt4acc-soleil-twin` Apptainer image.
3. Starts the twin with the embedded Tango database.
4. Uses test data stored under `tests/integration/data`.
5. Waits until the twin reports that all Tango processes are ready.
6. Runs a pytest integration smoke test.
7. Uploads the dt4acc twin log as an artifact.

Add a minimal pytest test under `tests/integration` that:

- loads a small pyAML accelerator configuration;
- instantiates `pyaml.Accelerator`;
- connects to the live Tango backend through `tango-pyaml`;
- reads the RF reference frequency from the dt4acc `RingSimulatorDevice`;
- asserts that the value is finite and positive.

The test should be opt-in, for example via `PYAML_DT4ACC_INTEGRATION=1`, so
the normal unit-test workflow remains fast and independent from Apptainer/Tango.

## Describe alternatives you've considered

One alternative is to mock Tango or use the existing dummy Tango backend. This
is useful for unit tests, but it does not validate the real deployment path
involving Apptainer, PyTango, Tango DB startup, dt4acc device registration, and
live device reads.

Another alternative is to run only the dt4acc integration tests in the dt4acc
repository. That validates the twin itself, but not the pyAML side of the
contract: loading an `Accelerator`, resolving Tango catalog references, and
reading values through the pyAML abstraction.

A larger end-to-end test could also write magnet or RF setpoints. That should
be added later, but the first step should be a small smoke test to stabilize
the CI infrastructure.

## Example

Example test behavior:

```python
accelerator = Accelerator.load("tests/integration/pyaml_dt4acc_twin.yaml")

rf = accelerator.live.get_rf_plant("RF")
reference_frequency = rf.frequency.get()

assert reference_frequency > 0.0
```

Example workflow behavior:

```bash
apptainer run \
  --bind tests/integration/data:/data:ro \
  dt4acc-soleil-twin.sif \
  --force-kill-db \
  --tango-host 127.0.0.1:10000 \
  --accelerator-setup-file /data/accelerator_setup.json \
  --lattice-file /data/SOLEIL_II_V3631_sym1_V001_database.m

PYAML_DT4ACC_INTEGRATION=1 python -m pytest -v tests/integration
```

## Additional context

The dt4acc twin already provides an Apptainer image with embedded Tango
database support. The required input files should be stored in
`tests/integration/data` so the workflow is self-contained and reproducible.

The initial test should target a stable read-only value, such as
`simulator/ringsimulator/ringsimulator/reference_frequency`, to avoid changing
the twin state during CI.

If the dt4acc image registry is private, the workflow should support optional
registry credentials via GitHub Actions secrets.

## Checklist

- [ ] I've assigned this issue to a project
- [ ] I've @-mentioned relevant people
