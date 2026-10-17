import warnings

import pytest

from pyaml.common.deprecation import deprecated


def test_function_warns_and_returns_value():
    @deprecated("old_func is deprecated")
    def old_func(x):
        return x * 2

    with pytest.warns(DeprecationWarning, match=r"^old_func is deprecated$"):
        assert old_func(3) == 6


def test_custom_message_is_included():
    @deprecated("use new_func instead")
    def old_func():
        return 1

    with pytest.warns(DeprecationWarning, match=r"^use new_func instead$"):
        old_func()


def test_method_warns_with_given_message():
    class Thing:
        @deprecated("Thing.old is deprecated: use other()")
        def old(self):
            return "ok"

    with pytest.warns(DeprecationWarning, match=r"^Thing\.old is deprecated: use other\(\)$"):
        assert Thing().old() == "ok"


def test_class_warns_on_instantiation_and_subclassing():
    @deprecated("OldThing is deprecated: use NewThing")
    class OldThing:
        def __init__(self, value):
            self.value = value

    with pytest.warns(DeprecationWarning, match=r"^OldThing is deprecated: use NewThing$"):
        obj = OldThing(5)
    assert obj.value == 5

    with pytest.warns(DeprecationWarning, match=r"^OldThing is deprecated: use NewThing$"):

        class SubThing(OldThing):
            pass


def test_warning_points_at_caller():
    @deprecated("old_func is deprecated")
    def old_func():
        return None

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        old_func()
    assert record[0].filename == __file__


def test_wrapped_function_keeps_metadata():
    @deprecated("documented is deprecated")
    def documented():
        """Docstring kept."""

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "Docstring kept."
    assert documented.__deprecated__ == "documented is deprecated"  # noqa: B009


def test_classmethod_over_deprecated_binds_and_warns():
    class Thing:
        @classmethod
        @deprecated("Thing.create is deprecated")
        def create(cls):
            return cls.__name__

    with pytest.warns(DeprecationWarning, match=r"^Thing\.create is deprecated$"):
        assert Thing.create() == "Thing"


def test_deprecated_over_classmethod_fails_at_definition():
    # typing_extensions.deprecated accepts classes and callables only; a
    # classmethod descriptor object is neither, so this stacking order is
    # rejected at class-definition time instead of silently losing binding.
    with pytest.raises(TypeError, match="must be applied to a class or callable"):

        class Thing:
            @deprecated("Thing.create is deprecated")
            @classmethod
            def create(cls):
                return cls.__name__


def test_staticmethod_composes_in_both_orders():
    class Thing:
        @staticmethod
        @deprecated("Thing.old_a is deprecated")
        def old_a():
            return "a"

        @deprecated("Thing.old_b is deprecated")
        @staticmethod
        def old_b():
            return "b"

    with pytest.warns(DeprecationWarning, match=r"^Thing\.old_a is deprecated$"):
        assert Thing.old_a() == "a"

    with pytest.warns(DeprecationWarning, match=r"^Thing\.old_b is deprecated$"):
        assert Thing.old_b() == "b"


def test_property_over_deprecated_warns_on_access():
    class Thing:
        def __init__(self):
            self._value = 7

        @property
        @deprecated("Thing.value is deprecated")
        def value(self):
            return self._value

    thing = Thing()
    with pytest.warns(DeprecationWarning, match=r"^Thing\.value is deprecated$"):
        assert thing.value == 7


def test_deprecated_over_property_fails_at_definition():
    # A property object is not callable, so stacking @deprecated on top of
    # @property is rejected at class-definition time; put @property on top.
    with pytest.raises(TypeError, match="must be applied to a class or callable"):

        class Thing:
            @deprecated("Thing.value is deprecated")
            @property
            def value(self):
                return 7
