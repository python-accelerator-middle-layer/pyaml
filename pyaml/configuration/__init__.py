"""
PyAML configuration module
"""

from .catalog import Catalog, CatalogConfigModel
from .factory import Factory
from .fileloader import get_root_folder, set_root_folder
from .manager import ConfigurationManager, UnsupportedConfigurationRootError
from .static_catalog import StaticCatalog

__all__ = [
    "ConfigurationManager",
    "UnsupportedConfigurationRootError",
    "Catalog",
    "CatalogConfigModel",
    "StaticCatalog",
    "Factory",
    "get_root_folder",
    "set_root_folder",
]
