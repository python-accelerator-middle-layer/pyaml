from typing import Any, Optional

from pyaml.control.deviceaccess import DeviceAccess


class DeviceAccessProxy(DeviceAccess):
    """
    Transparent DeviceAccess proxy.

    This proxy behaves like the wrapped DeviceAccess:
    - Unknown attribute access is forwarded to the current target (e.g. target._cfg).
    - Unknown attribute assignment is also forwarded to the target.
    - The proxy remains a stable handle whose target can be swapped at runtime.

    Notes
    -----
    Python does not route special methods (dunder methods like __len__)
    through __getattr__. If you need those, they must be explicitly defined.
    """

    __slots__ = ("_reference", "_target")

    def __init__(self, reference: str, target: DeviceAccess | None = None):
        object.__setattr__(self, "_reference", reference)
        object.__setattr__(self, "_target", target)

    # ------------------------------------------------------------------
    # Proxy-specific API
    # ------------------------------------------------------------------

    def set_target(self, target: DeviceAccess):
        """Replace the underlying target DeviceAccess."""
        object.__setattr__(self, "_target", target)

    def get_target(self) -> DeviceAccess:
        """
        Return the current target.

        Raises
        ------
        RuntimeError
            If the proxy has no target.
        """
        target = object.__getattribute__(self, "_target")
        if target is None:
            ref = object.__getattribute__(self, "_reference")
            raise RuntimeError(f"DeviceAccessProxy('{ref}') has no target attached.")
        return target

    # ------------------------------------------------------------------
    # Transparent forwarding
    # ------------------------------------------------------------------

    def __getattr__(self, name: str):
        """
        Forward any unknown attribute access to the target.

        This is called only if normal attribute lookup fails on the proxy itself.
        """
        return getattr(self.get_target(), name)

    def __setattr__(self, name: str, value: Any):
        """
        Forward attribute assignment to the target, except for proxy internals.
        """
        if name in ("_reference", "_target"):
            object.__setattr__(self, name, value)
            return
        setattr(self.get_target(), name, value)

    def __dir__(self):
        """
        Expose both proxy attributes and target attributes for introspection.
        """
        try:
            target_dir = dir(self.get_target())
        except RuntimeError:
            target_dir = []
        return sorted(set(list(super().__dir__()) + target_dir))

    def __repr__(self) -> str:
        """
        Helpful debug representation showing the current target.
        """
        ref = object.__getattribute__(self, "_reference")
        target = object.__getattribute__(self, "_target")
        return f"<DeviceAccessProxy reference={ref!r} target={target!r}>"

    # ------------------------------------------------------------------
    # DeviceAccess interface (explicit forwarding is still useful for typing)
    # ------------------------------------------------------------------

    def name(self) -> str:
        return self.get_target().name()

    def measure_name(self) -> str:
        return self.get_target().measure_name()

    def set(self, value: Any):
        self.get_target().set(value)

    def set_and_wait(self, value: Any):
        self.get_target().set_and_wait(value)

    def get(self):
        return self.get_target().get()

    def readback(self):
        return self.get_target().readback()

    def unit(self) -> str:
        return self.get_target().unit()

    def get_range(self) -> list[float]:
        return self.get_target().get_range()

    def check_device_availability(self) -> bool:
        return self.get_target().check_device_availability()
