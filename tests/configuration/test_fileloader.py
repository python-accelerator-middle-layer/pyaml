import json

import pytest

from pyaml import PyAMLException
from pyaml.configuration.fileloader import (
    FIELD_LOCATIONS_KEY,
    LOCATION_KEY,
    ROOT,
    LoadContext,
    RootFolder,
    _is_supported_file,
    load,
)


def test_rootfolder_uses_current_working_directory_when_no_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    root = RootFolder()

    assert root.get() == tmp_path.resolve()


def test_rootfolder_sets_explicit_path(tmp_path):
    root = RootFolder(tmp_path)

    assert root.get() == tmp_path.resolve()


def test_rootfolder_expands_relative_paths(tmp_path):
    root = RootFolder(tmp_path)

    assert root.expand_path("config.yaml") == (tmp_path / "config.yaml").resolve()


def test_rootfolder_expands_absolute_paths(tmp_path):
    root = RootFolder(tmp_path)
    absolute = (tmp_path / "nested" / "config.yaml").resolve()

    assert root.expand_path(absolute) == absolute


def test_rootfolder_set_updates_root(tmp_path):
    root = RootFolder(tmp_path)
    new_root = tmp_path / "other"

    before = root.expand_path("config.yaml")
    root.set(new_root)
    after = root.expand_path("config.yaml")

    assert root.get() == new_root.resolve()
    assert before == (tmp_path / "config.yaml").resolve()
    assert after == (new_root / "config.yaml").resolve()


def test_is_supported_file():
    assert _is_supported_file("config.yaml")
    assert _is_supported_file("config.yml")
    assert _is_supported_file("config.json")

    assert not _is_supported_file("config.txt")
    assert not _is_supported_file(1)
    assert not _is_supported_file(None)


def test_load_context_adds_and_removes_paths(tmp_path):
    ctx = LoadContext()
    path = tmp_path / "config.yaml"

    with ctx.loading(path):
        assert ctx.include_stack == [path]

    assert ctx.include_stack == []


def test_load_context_cleans_up_after_exception(tmp_path):
    ctx = LoadContext()
    path = tmp_path / "config.yaml"

    with pytest.raises(RuntimeError):
        with ctx.loading(path):
            raise RuntimeError

    assert ctx.include_stack == []


def test_load_yaml(tmp_path):
    ROOT.set(tmp_path)

    config = tmp_path / "config.yaml"
    config.write_text("a: 1\nb: hello\n")

    result = load("config.yaml")

    assert result["a"] == 1
    assert result["b"] == "hello"


def test_load_json(tmp_path):
    ROOT.set(tmp_path)

    config = tmp_path / "config.json"
    config.write_text(json.dumps({"a": 1, "b": "hello"}))

    result = load("config.json")

    assert result == {"a": 1, "b": "hello"}


def test_load_nested_yaml(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "child.yaml").write_text("answer: 42\n")

    (tmp_path / "parent.yaml").write_text("child: child.yaml\n")

    result = load("parent.yaml")

    assert result["child"]["answer"] == 42


def test_load_nested_json(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "child.json").write_text(json.dumps({"answer": 42}))

    (tmp_path / "parent.json").write_text(json.dumps({"child": "child.json"}))

    result = load("parent.json")

    assert result["child"]["answer"] == 42


def test_load_file_resolver_loads_nested_file(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "child.yaml").write_text("answer: 42\n")
    (tmp_path / "parent.yaml").write_text('target: "${file:subdir/child.yaml}"\n')

    result = load("parent.yaml")

    assert result["target"]["answer"] == 42


def test_load_env_resolver_resolves_environment_variable(tmp_path, monkeypatch):
    ROOT.set(tmp_path)

    monkeypatch.setenv("TANGO_HOST", "localhost:10000")
    (tmp_path / "config.yaml").write_text("host: ${env:TANGO_HOST}\n")

    result = load("config.yaml")

    assert result["host"] == "localhost:10000"


def test_load_env_resolver_missing_variable_raises(tmp_path, monkeypatch):
    ROOT.set(tmp_path)

    monkeypatch.delenv("TANGO_HOST", raising=False)
    (tmp_path / "config.yaml").write_text("host: ${env:TANGO_HOST}\n")

    with pytest.raises(PyAMLException, match="Environment variable 'TANGO_HOST' is not set"):
        load("config.yaml")


def test_interpolates_env_inside_string(tmp_path, monkeypatch):
    ROOT.set(tmp_path)
    monkeypatch.setenv("HOST", "localhost")
    monkeypatch.setenv("PORT", "5432")

    (tmp_path / "config.yaml").write_text("url: http://${env:HOST}:${env:PORT}\n")

    result = load("config.yaml")

    assert result["url"] == "http://localhost:5432"


def test_load_interpolates_env_multiple_times_in_one_string(tmp_path, monkeypatch):
    ROOT.set(tmp_path)

    monkeypatch.setenv("USER", "alice")

    (tmp_path / "config.yaml").write_text("message: hello ${env:USER}, ${env:USER}!\n")

    result = load("config.yaml")

    assert result["message"] == "hello alice, alice!"


def test_load_interpolated_file_resolver_inside_string_raises(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "child.yaml").write_text("answer: 42\n")
    (tmp_path / "config.yaml").write_text('value: "prefix-${file:child.yaml}-suffix"\n')

    with pytest.raises(PyAMLException, match="cannot be interpolated into a string"):
        load("config.yaml")


def test_load_interpolation_unknown_resolver_raises(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "config.yaml").write_text("value: prefix-${missing:VALUE}-suffix\n")

    with pytest.raises(PyAMLException, match="Unknown resolver 'missing'"):
        load("config.yaml")


def test_load_list_include_extends_list(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "items.yaml").write_text("- one\n- two\n")

    (tmp_path / "parent.yaml").write_text(
        """
    values:
    - start
    - items.yaml
    - end
    """.strip()
    )

    result = load("parent.yaml")

    assert result["values"] == [
        "start",
        "one",
        "two",
        "end",
    ]


def test_load_yaml_omits_locations_by_default(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "config.yaml").write_text("a: 1\n")

    result = load("config.yaml")

    assert LOCATION_KEY not in result
    assert FIELD_LOCATIONS_KEY not in result


def test_load_yaml_includes_locations_when_enables(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "config.yaml").write_text("a: 1\n")

    result = load("config.yaml", include_locations=True)

    assert LOCATION_KEY in result
    assert FIELD_LOCATIONS_KEY in result


def test_load_invalid_yaml_raises_pyaml_exception(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "bad.yaml").write_text("a:\n  - 1\n - 2\n")

    with pytest.raises(PyAMLException, match="bad.yaml"):
        load("bad.yaml")


def test_load_invalid_json_raises_pyaml_exception(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "bad.json").write_text('{"a": }')

    with pytest.raises(PyAMLException, match="bad.json"):
        load("bad.json")


def test_load_circular_include_raises_pyaml_exception(tmp_path):
    ROOT.set(tmp_path)

    (tmp_path / "a.yaml").write_text("b: b.yaml\n")
    (tmp_path / "b.yaml").write_text("a: a.yaml\n")

    with pytest.raises(PyAMLException, match="Circular file inclusion"):
        load("a.yaml")
