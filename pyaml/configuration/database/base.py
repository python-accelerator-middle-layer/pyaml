"""
Base backend database options.
"""

# import re, fnmatch
from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any, Optional

ItemData = dict[str, Any]
ItemDataGen = Generator[ItemData, None, None]


class ConfigBackend(ABC):
    """
    Base class for config backend database.
    """

    @property
    @abstractmethod
    def items(self) -> list[ItemData]:
        """List all items in the database

        Returns
        -------
        list[ItemData]
            List of item data in the database.
        """
        pass

    @abstractmethod
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
        pass

    # @abstractmethod
    # def find(self, multiples: bool = False, **kwargs) -> ItemDataGen:
    #     """Find an instance or instances that matches the search criteria.

    #     Parameters
    #     ----------
    #     multiples : bool, optional
    #         Find a single result or all results matching the provided
    #         information, by default False
    #     kwargs : Requested information.

    #     Returns
    #     -------
    #     ItemDataGen
    #         Generator for the item data.
    #     """
    #     pass

    # def find_regex(
    #     self,
    #     to_match: dict[str, Any],
    #     *,
    #     flags=re.IGNORECASE
    # ) -> ItemDataGen:
    #     """
    #     Yield all instances that match the given search criteria..
    #     """
    #     raise NotImplementedError

    @abstractmethod
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
        pass

    @abstractmethod
    def delete(self, id: str) -> None:
        """Delete an item from the database.

        Parameters
        ----------
        id : str
            Identifier of item.
        """
        pass
