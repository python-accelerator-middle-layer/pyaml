"""
PyAML configuration module
"""

from pathlib import Path

ROOT = {"path": Path.cwd().resolve()}


def set_root_folder(path: str | Path):
    """
    Set the root path for configuration files.
    """
    ROOT["path"] = Path(path).resolve()


def get_root_folder() -> Path:
    """
    Get the root path for configuration files.
    """
    return ROOT["path"]


def get_config_file_path(path: str | Path) -> Path:
    """Ensure the path is absolute and resolved."""
    path = Path(path)
    if not path.is_absolute():
        path = get_root_folder() / path
    return path.resolve()

from .models import load_from_yaml, load_from_json
from .FileLoader import load
from .Factory import depthFirstBuild
