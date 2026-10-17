"""
PyAML deprecation helper.

Thin re-export of :func:`typing_extensions.deprecated` (PEP 702), used to
mark functions, methods and classes that are being phased out.

The standard tool is used instead of a hand-rolled decorator because it
preserves descriptor binding when composed with ``@classmethod``,
``@staticmethod`` and ``@property``, warns on subclass creation as well as
instantiation, sets the ``__deprecated__`` attribute, and lets static type
checkers (mypy/pyright) flag call sites.

``typing_extensions`` is used rather than ``typing`` so the helper is also
available on Python < 3.13; the project therefore declares a direct
dependency on ``typing_extensions >= 4.5``.
"""

from typing_extensions import deprecated

__all__ = ["deprecated"]
