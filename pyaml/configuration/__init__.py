"""
PyAML configuration module
"""

from pathlib import Path
from typing import Union

ROOT = {"path": Path.cwd().resolve()}


def set_root_folder(path: Union[str, Path]):
    """
    Set the root path for configuration files.
    """
    ROOT["path"] = Path(path)


def get_root_folder() -> Path:
    """
    Get the root path for configuration files.
    """
    return ROOT["path"]

from .fileloader import load
from .factory import Factory
