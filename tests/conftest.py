import importlib
import importlib.machinery
import importlib.metadata
import pathlib
import sys
import types
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import at
import numpy as np
import pytest
from pydantic import BaseModel

from pyaml.configuration import ConfigurationManager
from pyaml.configuration.factory import Factory
from pyaml.control.readback_value import Value


@dataclass(frozen=True)
class TestPackageSpec:
    import_name: str
    distribution_name: str
    module_file: str
    local_path: pathlib.Path


_TEST_PACKAGES = {
    "tango-pyaml": TestPackageSpec(
        import_name="tango.pyaml.controlsystem",
        distribution_name="tango-pyaml",
        module_file="tango/pyaml/controlsystem.py",
        local_path=pathlib.Path("tests/dummy_cs/tango-pyaml"),
    ),
    "pyaml_external": TestPackageSpec(
        import_name="pyaml_external.external_magnet_model",
        distribution_name="pyaml_external",
        module_file="pyaml_external/external_magnet_model.py",
        local_path=pathlib.Path("tests/external"),
    ),
}
_TESTS_DIR = pathlib.Path(__file__).parent.resolve()
_CONFIG_DIR = _TESTS_DIR / "config"


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
    package_path = _resolve_test_package_path(info)

    with _installed_test_packages([package_path], skip_if_installed=(package_name,)):
        yield package_name


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


def _resolve_test_package_path(info: dict) -> pathlib.Path:
    package_path_value = info.get("path")
    if package_path_value is None:
        raise RuntimeError("No package_path defined for install_test_package fixture")

    package_path = pathlib.Path(package_path_value).resolve()
    if not package_path.exists():
        raise FileNotFoundError(f"Package path not found: {package_path}")
    if not ((package_path / "pyproject.toml").exists() or (package_path / "setup.py").exists()):
        raise RuntimeError(f"No pyproject.toml or setup.py found in {package_path}")
    return package_path


def _module_available(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError:
        return False
    return True


def _imported_module_path(module_name: str) -> pathlib.Path | None:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None

    module_file = getattr(module, "__file__", None)
    if module_file is None:
        return None
    return pathlib.Path(module_file).resolve()


def _installed_module_path(spec: TestPackageSpec) -> pathlib.Path | None:
    try:
        distribution = importlib.metadata.distribution(spec.distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None

    module_path = pathlib.Path(distribution.locate_file(spec.module_file)).resolve()
    return module_path if module_path.exists() else None


def _module_matches_test_package(package_name: str, package_path: pathlib.Path) -> bool:
    spec = _TEST_PACKAGES.get(package_name)
    if spec is None:
        return False

    module_path = _imported_module_path(spec.import_name)
    if module_path is None:
        return False
    if module_path.is_relative_to(package_path):
        return True

    installed_module_path = _installed_module_path(spec)
    return installed_module_path is not None and module_path == installed_module_path


def _purge_modules(package_roots: list[str]) -> None:
    for root in package_roots:
        for module_name in list(sys.modules):
            if module_name == root or module_name.startswith(f"{root}."):
                sys.modules.pop(module_name, None)


def _expose_namespace_packages(package_path: pathlib.Path) -> None:
    for child in package_path.iterdir():
        if child.name.startswith(".") or not child.is_dir():
            continue
        if (child / "__init__.py").exists():
            continue

        module = sys.modules.get(child.name)
        if module is None:
            try:
                module = importlib.import_module(child.name)
            except ModuleNotFoundError:
                module = types.ModuleType(child.name)
                module.__path__ = []
                module.__package__ = child.name
                module.__spec__ = importlib.machinery.ModuleSpec(child.name, loader=None, is_package=True)
                sys.modules[child.name] = module

        module_path = list(getattr(module, "__path__", []))
        child_str = str(child)
        if child_str not in module_path:
            module_path.append(child_str)
            module.__path__ = module_path


@contextmanager
def _installed_test_packages(
    package_paths: list[pathlib.Path],
    *,
    skip_if_installed: tuple[str, ...] = (),
):
    if skip_if_installed:
        package_map = {
            package_name: _TEST_PACKAGES[package_name].local_path.resolve()
            for package_name in skip_if_installed
            if package_name in _TEST_PACKAGES
        }
        if package_map and all(
            _module_matches_test_package(package_name, package_path)
            for package_name, package_path in package_map.items()
        ):
            yield
            return

    package_roots = list(
        dict.fromkeys(root for package_path in package_paths for root in _discover_package_roots(package_path))
    )
    path_strings = [str(path) for path in package_paths]

    _purge_modules(package_roots)
    for path_string in reversed(path_strings):
        if path_string not in sys.path:
            sys.path.insert(0, path_string)
    for package_path in package_paths:
        _expose_namespace_packages(package_path)
    importlib.invalidate_caches()

    try:
        yield
    finally:
        _purge_modules(package_roots)
        for path_string in path_strings:
            while path_string in sys.path:
                sys.path.remove(path_string)
        importlib.invalidate_caches()


@pytest.fixture(scope="session", autouse=True)
def install_default_test_packages():
    package_paths = [spec.local_path.resolve() for spec in _TEST_PACKAGES.values()]
    with _installed_test_packages(
        package_paths,
        skip_if_installed=tuple(_TEST_PACKAGES),
    ):
        yield


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
    return _CONFIG_DIR


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
    config_root_path,
) -> tuple[pathlib.Path]:
    return (config_root_path / "tune_monitor.yaml",)


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
