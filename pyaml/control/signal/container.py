from abc import ABCMeta, abstractmethod
from typing import TypeVar, Generic

from . import arun

SignalDatatypeT = TypeVar("SignalDatatypeT")
RSignalT = TypeVar("RSignalT")  # "read" signal-like object
WSignalT = TypeVar("WSignalT")  # "write" signal-like object


class Readback(Generic[SignalDatatypeT, RSignalT], metaclass=ABCMeta):
    """Abstract readback class"""

    def __init__(self, r_signal: RSignalT):
        self._r_sig: RSignalT = r_signal

    @abstractmethod
    async def async_get(self) -> SignalDatatypeT: ...

    def get(self) -> SignalDatatypeT:
        """Synchronous wrapper around `async_get()`."""
        return arun(self.async_get())

    @abstractmethod
    async def async_read(self) -> SignalDatatypeT: ...

    def read(self) -> SignalDatatypeT:
        return arun(self.async_read())


class Setpoint(Generic[SignalDatatypeT, WSignalT, RSignalT], metaclass=ABCMeta):
    """Abstract setpoint class"""

    def __init__(self, w_signal: WSignalT, r_signal: RSignalT | None = None):
        self._w_sig: WSignalT = w_signal
        self._r_sig: RSignalT | None = r_signal  # used only for `set_and_wait()`
        self._has_r_sig: bool = r_signal is not None

    @abstractmethod
    async def async_get(self) -> SignalDatatypeT: ...

    def get(self) -> SignalDatatypeT:
        """Synchronous wrapper around `async_get()`."""
        return arun(self.async_get())

    @abstractmethod
    async def async_read(self) -> SignalDatatypeT: ...

    def read(self) -> SignalDatatypeT:
        """Synchronous wrapper around `async_read()`."""
        return arun(self.async_read())

    @abstractmethod
    async def async_set(self, value): ...

    async def _complete_set(self, value):
        status = await self.async_set(value)
        await status  # Wait for completion before returning
        return status

    def set(self, value):
        """Synchronous wrapper around `async_set()`."""
        return arun(self._complete_set(value))

    @abstractmethod
    async def async_set_and_wait(self, value) -> None: ...

    def set_and_wait(self, value) -> None:
        """Synchronous wrapper around `async_set_and_wait()`."""
        return arun(self.async_set_and_wait(value))
