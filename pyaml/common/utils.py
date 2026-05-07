"""Module for utility functions."""


def __pyaml_repr__(obj):
    """
    Returns a string representation of a pyaml object
    """

    attrs = {}

    # Instance attributes
    for k, v in obj.__dict__.items():
        # Exclude private attributes
        if not k.startswith("_"):
            attrs[k] = v

    # Properties
    for name, attr in vars(type(obj)).items():
        if isinstance(attr, property):
            try:
                attrs[name] = getattr(obj, name)
            except Exception as e:
                attrs[name] = f"<error: {e}>"

    parts = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
    return f"{obj.__class__.__name__}({parts})"
