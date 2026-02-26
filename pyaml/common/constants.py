"""
PyAML global constants

.. data:: HORIZONTAL_KICK_SIGN

    Horizontal kick sign convention for both kick an kick angle (default: -1).

.. data:: ACTION_APPLY

    Action identifier for callback in measurement tools
    Triggered just after exitation has been sent

.. data:: ACTION_RESTORE

    Action identifier for callback in measurement tools
    Triggered just after exitation has been restored

.. data:: ACTION_MEASURE

    Action identifier for callback in measurement tools
    Triggered just after measurement

"""

HORIZONTAL_KICK_SIGN: float = -1.0

ACTION_APPLY: int = 0
ACTION_RESTORE: int = 1
ACTION_MEASURE: int = 2
