"""
PyAML configuration module
"""

from .catalog import Catalog, CatalogConfigModel, CatalogResolver
from .factory import Factory
from .fileloader import get_root_folder, set_root_folder
from .manager import ConfigurationManager, UnsupportedConfigurationRootError
from .static_catalog import StaticCatalog
from .static_catalog_entry import StaticCatalogEntry

__all__ = [
    "ConfigurationManager",
    "UnsupportedConfigurationRootError",
    "Catalog",
    "CatalogConfigModel",
    "CatalogResolver",
    "StaticCatalog",
    "StaticCatalogEntry",
    "Factory",
    "get_root_folder",
    "set_root_folder",
]
