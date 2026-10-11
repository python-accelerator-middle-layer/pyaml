"""
PyAML deprecation helper.

Provides the ``deprecated`` decorator, used to mark functions, methods and
classes that are being phased out. Using a decorated object emits a
``DeprecationWarning`` pointing at the caller.
"""

import functools
import warnings
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def deprecated(message: str | None = None) -> Callable[[T], T]:
    """
    Mark a function, method or class as deprecated.

    Each use emits a ``DeprecationWarning`` that names the deprecated object
    and, if given, the custom ``message``.

    Parameters
    ----------
    message : str, optional
        Extra guidance appended to the warning, e.g. the replacement to use.

    Returns
    -------
    Callable
        A decorator that returns the wrapped object unchanged in behaviour.

    Examples
    --------
    >>> @deprecated("use new_api_function instead")
    ... def old_api_function():
    ...     return 1
    """

    def decorator(obj: T) -> T:
        name = getattr(obj, "__qualname__", getattr(obj, "__name__", repr(obj)))
        text = f"{name} is deprecated"
        if message:
            text = f"{text}: {message}"

        if isinstance(obj, type):
            original_init: Any = obj.__init__

            @functools.wraps(original_init)
            def init_wrapper(self, *args, **kwargs):
                warnings.warn(text, DeprecationWarning, stacklevel=2)
                return original_init(self, *args, **kwargs)

            obj.__init__ = init_wrapper  # type: ignore[misc]
            return obj

        @functools.wraps(obj)  # type: ignore[arg-type]
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(text, DeprecationWarning, stacklevel=2)
            return obj(*args, **kwargs)  # type: ignore[operator]

        return wrapper  # type: ignore[return-value]

    return decorator
