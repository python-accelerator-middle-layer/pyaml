import pytest
import subprocess
import sys
import pathlib
import numpy as np
from pyaml.control.readback_value import Value


@pytest.fixture
def install_test_package(request):
    """
    Temporarily install a test package and uninstall it after the test.

    The test must provide a dictionary as parameter with:
    - 'name': name of the installable package (used for pip uninstall)
    - 'path': relative path to the package folder (e.g. 'tests/mon_dir')

    Example:
    --------
    @pytest.mark.parametrize("install_test_package", [{
        "name": "mon_package",
        "path": "tests/mon_dir"
    }], indirect=True)
    def test_x(install_test_package):
        ...
    """
    info = request.param
    package_name = info["name"]
    package_path = pathlib.Path(info["path"]).resolve()

    if not package_path.exists():
        raise FileNotFoundError(f"Package path not found: {package_path}")

    if not ((package_path / "pyproject.toml").exists() or (package_path / "setup.py").exists()):
        raise RuntimeError(f"No pyproject.toml or setup.py found in {package_path}")

    # Install package
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet", "--editable", str(package_path)
    ])
    # Test the import.
    import importlib
    # Ensure its path is importable
    if str(package_path) not in sys.path:
        sys.path.insert(0, str(package_path))

    # Remove from sys.modules to avoid caching issues
    sys.modules.pop(package_name, None)

    # Import the module freshly
    module = importlib.import_module(package_name)

    yield module


    # Uninstall package
    subprocess.call([
        sys.executable, "-m", "pip", "uninstall", "-y", package_name
    ])


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
