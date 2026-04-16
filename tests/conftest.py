import importlib
import pathlib
import sys
import types
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import at
import numpy as np
import pytest
from pydantic import BaseModel

from pyaml.configuration import ConfigurationManager
from pyaml.configuration.factory import BuildStrategy, Factory
from pyaml.control.readback_value import Value


@pytest.fixture
def install_test_package(request):
    """
    Temporarily expose a local test package on ``sys.path`` for the test.

    The test must provide a dictionary as parameter with:
    - 'name': logical package name
    - 'path': relative path to the package folder (e.g. 'tests/my_dir').
      Optional, replaced by package name if absent.

    Example:
    --------
    @pytest.mark.parametrize("install_test_package", [{
        "name": "my_package",
        "path": "tests/my_dir"
    }], indirect=True)
    def test_x(install_test_package):
        ...
    """

    info = request.param
    if info is None:
        yield None
        return
    package_name = info["name"]
    package_path = None
    if info["path"] is not None:
        package_path = pathlib.Path(info["path"]).resolve()
        if not package_path.exists():
            raise FileNotFoundError(f"Package path not found: {package_path}")

    if package_path is None:
        raise RuntimeError("No package_path defined for install_test_package fixture")

    if not ((package_path / "pyproject.toml").exists() or (package_path / "setup.py").exists()):
        raise RuntimeError(f"No pyproject.toml or setup.py found in {package_path}")

    package_path_str = str(package_path)
    package_roots = _discover_package_roots(package_path)

    _purge_modules(package_roots)
    if package_path_str not in sys.path:
        sys.path.insert(0, package_path_str)
    importlib.invalidate_caches()

    yield package_name

    _purge_modules(package_roots)
    while package_path_str in sys.path:
        sys.path.remove(package_path_str)
    importlib.invalidate_caches()


def _discover_package_roots(package_path: pathlib.Path) -> list[str]:
    roots: list[str] = []

    for top_level_file in package_path.glob("*.egg-info/top_level.txt"):
        roots.extend(line.strip() for line in top_level_file.read_text().splitlines() if line.strip())

    if roots:
        return list(dict.fromkeys(roots))

    for child in package_path.iterdir():
        if child.name.startswith("."):
            continue
        if child.is_dir():
            roots.append(child.name)
        elif child.suffix == ".py":
            roots.append(child.stem)

    return list(dict.fromkeys(roots))


def _purge_modules(package_roots: list[str]) -> None:
    for root in package_roots:
        for module_name in list(sys.modules):
            if module_name == root or module_name.startswith(f"{root}."):
                sys.modules.pop(module_name, None)


@pytest.fixture
def accelerator_from_fragments():
    """
    Build an accelerator explicitly from a list of configuration fragments.
    """

    def _build(*fragments, ignore_external: bool = False):
        manager = ConfigurationManager()
        for fragment in fragments:
            manager.add(fragment)
        return manager.build(ignore_external=ignore_external)

    return _build


@pytest.fixture
def config_root_path() -> pathlib.Path:
    """
    Returns the absolute path to the `tests/config` directory as a Path.
    """
    return (pathlib.Path(__file__).parent / "config").resolve()


@pytest.fixture
def config_root_dir(config_root_path):
    """
    Returns the absolute path to the `tests/config` directory.
    """
    return str(config_root_path)


@pytest.fixture
def config_manager_base_config(config_root_path) -> pathlib.Path:
    return config_root_path / "config_manager_base.yaml"


@pytest.fixture
def config_manager_simulator_json(config_root_path) -> pathlib.Path:
    return config_root_path / "config_manager_simulator.json"


@pytest.fixture
def ebs_lattice_file(config_root_path) -> pathlib.Path:
    return (config_root_path / "sr" / "lattices" / "ebs.mat").resolve()


@pytest.fixture
def simulator_fragment_factory(ebs_lattice_file):
    def _build(name: str) -> dict:
        return {
            "type": "pyaml.lattice.simulator",
            "name": name,
            "lattice": str(ebs_lattice_file),
        }

    return _build


@pytest.fixture
def sr_base_fragment(config_root_path) -> pathlib.Path:
    return config_root_path / "config_manager_sr_base.yaml"


@pytest.fixture
def sr_arrays_fragment(config_root_path) -> pathlib.Path:
    return config_root_path / "config_manager_sr_arrays.yaml"


@pytest.fixture
def sr_devices_fragment(config_root_path) -> pathlib.Path:
    return config_root_path / "config_manager_sr_devices.yaml"


@pytest.fixture
def sr_configuration_fragments(
    sr_base_fragment,
    sr_arrays_fragment,
    sr_devices_fragment,
) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    return (sr_base_fragment, sr_arrays_fragment, sr_devices_fragment)


@pytest.fixture
def tune_monitor_devices_fragment(config_root_path) -> pathlib.Path:
    return config_root_path / "config_manager_tune_monitor_devices.yaml"


@pytest.fixture
def tune_monitor_configuration_fragments(
    sr_base_fragment,
    tune_monitor_devices_fragment,
) -> tuple[pathlib.Path, pathlib.Path]:
    return (sr_base_fragment, tune_monitor_devices_fragment)


@pytest.fixture
def http_config_server():
    @contextmanager
    def _serve(routes: dict[str, str | tuple[str, str, int]]):
        normalized_routes: dict[str, tuple[bytes, str, int]] = {}
        for path, response in routes.items():
            body: str
            content_type = "text/plain"
            status = 200
            if isinstance(response, tuple):
                body, content_type, status = response
            else:
                body = response
            normalized_routes[path] = (body.encode("utf-8"), content_type, status)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                payload, content_type, status = normalized_routes.get(
                    self.path,
                    (b"not found", "text/plain", 404),
                )
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            yield base_url
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    return _serve


@pytest.fixture
def value_scalar():
    """Return a basic scalar Value instance."""
    return Value(3.14)


@pytest.fixture
def value_array():
    """Return a Value instance containing a NumPy array."""
    return Value(np.array([10, 20, 30]))


@pytest.fixture
def value_matrix():
    """Return a list of Value instances wrapping NumPy arrays."""
    return [
        Value(np.array([10, 20, 30])),
        Value(np.array([100, 400, 900])),
        Value(np.array([1000, 4000, 9000])),
    ]


@pytest.fixture
def scalar_vector():
    """Return a vector of scalars for broadcasting tests."""
    return np.full(3, 2)


@pytest.fixture
def broadcast_matrix():
    """Return a 3x3 matrix filled with 2s for broadcasted multiplication tests."""
    return np.full((3, 3), 2)


# ────────────── Simulated module ──────────────


class MockConfig(BaseModel):
    name: str


class MockElement:
    def __init__(self, config):
        self.name = config.name


mock_module = types.ModuleType("mock_module")
mock_module.ConfigModel = MockConfig
mock_module.PYAMLCLASS = "MockElement"
mock_module.MockElement = MockElement


# ────────────── Custom strategy ──────────────


class MockStrategy(BuildStrategy):
    def can_handle(self, module, config_dict):
        return config_dict.get("custom") is True

    def build(self, module, config_dict):
        name = config_dict.get("name", "default")
        return MockElement(config=MockConfig(name=f"custom_{name}"))


# ────────────── Pytest fixtures ──────────────


@pytest.fixture(scope="module", autouse=True)
def inject_mock_module():
    """Inject a simulated external module into sys.modules."""
    sys.modules["mock_module"] = mock_module
    yield
    sys.modules.pop("mock_module", None)


@pytest.fixture(autouse=True)
def clear_factory_registry():
    """Clear element registry before/after each test."""
    Factory.clear()
    yield
    Factory.clear()


@pytest.fixture(autouse=True)
def register_mock_strategy():
    """Register and unregister mock build strategy."""
    strategy = MockStrategy()
    Factory.register_strategy(strategy)
    yield
    Factory.remove_strategy(strategy)


# -----------------------
# Linkers fixtures
# -----------------------


@pytest.fixture
def lattice_with_famnames() -> at.Lattice:
    """Lattice with duplicate FamName to test multi-match and first-element behavior."""
    qf1 = at.elements.Quadrupole("QF_1", 0.2)
    qf1.FamName = "QF"
    qf2 = at.elements.Quadrupole("QF_2", 0.25)
    qf2.FamName = "QF"
    qd1 = at.elements.Quadrupole("QD_1", 0.3)
    qd1.FamName = "QD"
    return at.Lattice([qf1, qf2, qd1], energy=3e9)


@pytest.fixture
def lattice_with_custom_attr() -> at.Lattice:
    """Lattice where a custom attribute (e.g., 'Tag') is set on elements."""
    d1 = at.elements.Drift("D1", 1.0)
    d1.Tag = "D1"
    qf = at.elements.Quadrupole("QF", 0.2)
    qf.Tag = "QF"
    qf2 = at.elements.Quadrupole("QF2", 0.2)
    qf2.Tag = "QF"
    qd = at.elements.Quadrupole("QD", 0.3)
    qd.Tag = "QD"
    return at.Lattice([d1, qf, qf2, qd], energy=3e9)
