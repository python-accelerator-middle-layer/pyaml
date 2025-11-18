import types

import at
import pytest
import subprocess
import sys
import pathlib
import numpy as np
from pyaml.control.readback_value import Value
from pydantic import BaseModel
from pyaml.configuration.factory import Factory,BuildStrategy


@pytest.fixture
def install_test_package(request):
    """
    Temporarily install a test package and uninstall it after the test.

    The test must provide a dictionary as parameter with:
    - 'name': name of the installable package (used for pip uninstall)
    - 'path': relative path to the package folder (e.g. 'tests/my_dir'). Optional, replaced by package name if absent.

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
        raise RuntimeError(f"No package_path defined for install_test_package fixture")

    if not ((package_path / "pyproject.toml").exists() or (package_path / "setup.py").exists()):
        raise RuntimeError(f"No pyproject.toml or setup.py found in {package_path}")    

    # Install package in a classis way, `--editable` create a .pth entry in conda env which is imcompatible with submodule
    if package_path is not None:
        subprocess.check_call([
            sys.executable, "-m", "pip", "--quiet", "install", str(package_path)
        ])

    yield package_name

    # Do not uninstall packe at the end tp speed up tests a bit
    #subprocess.call([
    #    sys.executable, "-m", "pip", "uninstall", "-y", package_name
    #])


@pytest.fixture
def config_root_dir():
    """
    Returns the absolute path to the `tests/config` directory.
    """
    return str((pathlib.Path(__file__).parent / "config").resolve())


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
    qf1 = at.elements.Quadrupole('QF_1', 0.2); qf1.FamName = 'QF'
    qf2 = at.elements.Quadrupole('QF_2', 0.25); qf2.FamName = 'QF'
    qd1 = at.elements.Quadrupole('QD_1', 0.3); qd1.FamName = 'QD'
    return at.Lattice([qf1, qf2, qd1], energy=3e9)


@pytest.fixture
def lattice_with_custom_attr() -> at.Lattice:
    """Lattice where a custom attribute (e.g., 'Tag') is set on elements."""
    d1 = at.elements.Drift('D1', 1.0);         setattr(d1, "Tag", "D1")
    qf = at.elements.Quadrupole('QF', 0.2);    setattr(qf, "Tag", "QF")
    qf2 = at.elements.Quadrupole('QF2', 0.2);  setattr(qf2, "Tag", "QF")
    qd = at.elements.Quadrupole('QD', 0.3);    setattr(qd, "Tag", "QD")
    return at.Lattice([d1, qf, qf2, qd], energy=3e9)
