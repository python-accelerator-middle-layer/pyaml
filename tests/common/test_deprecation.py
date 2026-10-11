import warnings

import pytest

from pyaml.common.deprecation import deprecated


def test_function_warns_and_returns_value():
    @deprecated()
    def old_func(x):
        return x * 2

    with pytest.warns(DeprecationWarning, match="old_func is deprecated"):
        assert old_func(3) == 6


def test_custom_message_is_included():
    @deprecated("use new_func instead")
    def old_func():
        return 1

    with pytest.warns(DeprecationWarning, match="use new_func instead"):
        old_func()


def test_method_warns_with_qualified_name():
    class Thing:
        @deprecated("use other()")
        def old(self):
            return "ok"

    with pytest.warns(DeprecationWarning, match="Thing.old is deprecated: use other"):
        assert Thing().old() == "ok"


def test_class_warns_on_instantiation():
    @deprecated("use NewThing")
    class OldThing:
        def __init__(self, value):
            self.value = value

    with pytest.warns(DeprecationWarning, match="OldThing is deprecated: use NewThing"):
        obj = OldThing(5)
    assert obj.value == 5


def test_warning_points_at_caller():
    @deprecated()
    def old_func():
        return None

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        old_func()
    assert record[0].filename == __file__


def test_wrapped_function_keeps_metadata():
    @deprecated()
    def documented():
        """Docstring kept."""

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "Docstring kept."
