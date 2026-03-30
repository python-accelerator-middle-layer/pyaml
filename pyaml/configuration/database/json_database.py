"""
Backend implemenation using json.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from .base import BaseConfigBackend, ItemData, ItemDataGen

logger = logging.getLogger(__name__)


class JsonConfigBackend(BaseConfigBackend):
    """
    JSON database.

    The information is stored in a single large dictionary.

    Parameters
    ----------
    path : str
        Path to JSON file.
    initialize : bool, optional
        Initialize a new JSON file, by default False.
    cfg_path : Optional[str], optional
        Path to config file, by default None.
    """

    # TODO: is the config file required?

    def __init__(self, path: str, initialize: bool = False, cfg_path: Optional[str] = None) -> None:
        # Create empty in-memory database
        self._load_cache: dict[str, ItemData] = {}

        # TODO: handle relative path
        self.path = path

        # if cfg_path is not None:
        #     cfg_dir = os.path.dirname(cfg_path)
        #     self.path = utils.build_abs_path(cfg_dir, path)
        # else:
        #     self.path = path

        # If requested, create a new JSON file
        if initialize:
            self.initialize()
        else:
            self.load()

    def initialize(self):
        """Initialize a new JSON database.

        Raises
        ------
        PermissionError
            Error raised if the file already exist to not overwrite.
        """

        # Do not overwrite existing databases
        if os.path.exists(self.path) and os.stat(self.path).st_size > 0:
            raise PermissionError("File {} already exists. Can not initialize a new database.".format(self.path))
        # Dump an empty dictionary
        self.store({})

    def store(self, db: dict[str, ItemData]) -> None:
        """Write the database into the JSON file.

        It is done in two steps to avoid corrupting the file.

        Parameters
        ----------
        db : dict[str, ItemData]
            Dictionary to store in the database.
        """

        directory = Path(self.path).parent
        temp_path = None

        try:
            # Create the temporary file
            with tempfile.NamedTemporaryFile(
                dir=directory,
                delete=False,
                mode="w",
                encoding="utf-8",
            ) as tmp:
                json.dump(db, tmp, indent=2)
                temp_path = Path(tmp.name)

            # Copy the temporary file to the real file
            temp_path.replace(self.path)

        except Exception as ex:
            logger.debug("JSON db write failed: %s", ex, exc_info=ex)

            # Cleanup temp file if it exists
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
            raise

    def load(self):
        """Load the database from file."""

        if not self._load_cache:
            try:
                # Load the database from file
                with open(self.path) as f:
                    raw_json = f.read()

                # Allow for empty files to be considered valid databases:
                self._load_cache = json.loads(raw_json) if raw_json else {}

            except FileNotFoundError:
                raise

    @property
    def items(self) -> list[ItemData]:
        """List all items in the database

        Returns
        -------
        list[ItemData]
            List of item data in the database.
        """
        db = self._load_cache
        return list(db.values())

    def get_by_id(self, id: str) -> Optional[ItemData]:
        """Get item by identifier.

        Parameters
        ----------
        id : str
            Identifier of item.

        Returns
        -------
        Optional[ItemData]
            Data for item.
        """
        db = self._load_cache
        if db is not None:
            return db.get(id)

    def save(self, id: str, data: dict[str, Any], insert: bool = True) -> None:
        """Save data to the database.

        Parameters
        ----------
        id : str
            Identifier of item.
        data : dict[str, Any]
            Data to put into the database.
        insert : bool, optional
            Insert a new item in the database, by default True.
        """

        db = self._load_cache

        # Add a new item
        if insert:
            if id in db:
                raise ValueError(f"Item {id} already exists")

            # Add the id to the item and add to database
            db[id] = {**data, "id": id}

        # Change item
        else:
            if id not in db:
                raise KeyError(f"No item found {id}")
            db[id].update(data)

        # Save to JSON file
        self.store(db)

    def delete(self, id: str) -> None:
        """Delete an item from the database.

        Parameters
        ----------
        id : str
            Identifier of item.
        """

        db = self._load_cache
        if id not in db:
            raise KeyError(f"No item found {id}")
        db.pop(id)

        # Save to JSON file
        self.store(db)
