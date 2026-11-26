"""Build pyAML accelerators from the pyaml-test-lattice FODO 1 GeV 6D fixtures."""

from pathlib import Path

from pyaml_test_lattice import configurations, lattices

from pyaml.accelerator import Accelerator
from pyaml.configuration import ConfigurationManager

FODO_LATTICE_KEY = "fodo_1gev_6d.json"


def load_fodo_fragment(config_key: str, control_overrides: dict | None = None) -> dict:
    """Load one pyaml-test-lattice FODO config fragment as a plain dict.

    The ``lattice`` reference is overridden since it lives in a different
    package subtree (``data/lattice``) than the config fragment
    (``data/configuration``).

    ``control_overrides`` entries are merged into every control system of the
    fragment, for instance an EPICS PV ``prefix``.
    """
    config_path = Path(configurations[config_key])
    manager = ConfigurationManager()
    manager.add(config_path)
    fragment = manager.to_dict()

    fragment["simulators"][0]["lattice"] = str(Path(lattices[FODO_LATTICE_KEY]))

    for control in fragment.get("controls", []):
        control.update(control_overrides or {})

    return fragment


def build_fodo_accelerator(config_key: str, control_overrides: dict | None = None) -> Accelerator:
    """Build an Accelerator from one pyaml-test-lattice FODO config fragment."""
    configuration_manager = ConfigurationManager()
    configuration_manager.add(load_fodo_fragment(config_key, control_overrides))

    return Accelerator.from_dict(configuration_manager.to_dict())
