"""
Backend implementation using yaml.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import yaml

from .base import BaseConfigBackend, ItemData

logger = logging.getLogger(__name__)


class YamlConfigBackend(BaseConfigBackend):
    """
    YAML database.

    The information is stored in a single large dictionary.

    Parameters
    ----------
    path : str
        Path to YAML file.
    initialize : bool, optional
        Initialize a new YAML file, by default False.
    cfg_path : Optional[str], optional
        Path to config file, by default None.
    """

    def __init__(self, path: str, initialize: bool = False, cfg_path: Optional[str] = None) -> None:
        # Create empty in-memory database
        self._load_cache: dict[str, ItemData] = {}

        # TODO: handle relative path
        self.path = path

        # If requested, create a new YAML file
        if initialize:
            self.initialize()
        else:
            self.load()

    def initialize(self) -> None:
        """Initialize a new YAML database.

        Raises
        ------
        PermissionError
            Raised if the file already exists and is not empty.
        """
        if os.path.exists(self.path) and os.stat(self.path).st_size > 0:
            raise PermissionError(f"File {self.path} already exists. Can not initialize a new database.")

        self.store({})

    def store(self, db: dict[str, ItemData]) -> None:
        """Write the database into the YAML file.

        It is done in two steps to avoid corrupting the file.
        """
        directory = Path(self.path).parent
        temp_path: Optional[Path] = None

        try:
            with tempfile.NamedTemporaryFile(
                dir=directory,
                delete=False,
                mode="w",
                encoding="utf-8",
            ) as tmp:
                yaml.safe_dump(db, tmp, sort_keys=False)
                temp_path = Path(tmp.name)

            temp_path.replace(self.path)

        except Exception as ex:
            logger.debug("YAML db write failed: %s", ex, exc_info=ex)
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
            raise

    def load(self) -> None:
        """Load the database from file."""
        if not self._load_cache:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)

            self._load_cache = loaded if loaded else {}

    @property
    def items(self) -> list[ItemData]:
        """List all items in the database."""
        return list(self._load_cache.values())

    def get_by_id(self, id: str) -> Optional[ItemData]:
        """Get item by identifier."""
        return self._load_cache.get(id)

    def save(self, id: str, data: dict[str, Any], insert: bool = True) -> None:
        """Save data to the database."""
        db = self._load_cache

        if insert:
            if id in db:
                raise ValueError(f"Item {id} already exists")
            db[id] = {**data, "id": id}
        else:
            if id not in db:
                raise KeyError(f"No item found {id}")
            db[id].update(data)

        self.store(db)

    def delete(self, id: str) -> None:
        """Delete an item from the database."""
        db = self._load_cache
        if id not in db:
            raise KeyError(f"No item found {id}")

        db.pop(id)
        self.store(db)
