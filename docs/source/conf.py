# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


import re

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "pyaml"
copyright = "2026, pyAML Collaboration"
author = "pyAML Collaboration"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "myst_parser",
    "sphinx_copybutton",
]

autosummary_generate = True

# Maybe add "undoc-members": True here later
autodoc_default_options = {"members": True, "show-inheritance": True, "member-order": "groupwise"}

autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"
autodoc_typehints_format = "short"
# autosummary_generate_overwrite = False
# autosummary_ignore_module_all = False
# Class docstrings document the constructor parameters; __init__ docstrings are not rendered.
autoclass_content = "class"

napoleon_use_rtype = False  # More legible
# napoleon_numpy_docstring = False  # Force consistency, leave only Google
napoleon_custom_sections = ["Configuration"]

templates_path = ["_templates"]
exclude_patterns = []


# -- Class docstring "Methods"/"Attributes" sections ---------------------------
# Class docstrings list their methods and attributes so that ``help(obj)`` is
# self-contained. autodoc already documents each member from its own docstring,
# so on the rendered page the ``.. method::`` / ``.. attribute::`` blocks that
# napoleon emits for these sections are collapsed into a linked summary table
# instead of a second full description of every member.

_MEMBER_DIRECTIVE = re.compile(r"^\.\. (method|attribute):: (\S[^(]*)")
_SUMMARY_TITLES = {"attribute": ("Attributes", "attr"), "method": ("Methods", "meth")}


def _read_member_block(lines, i):
    """Return ``(kind, member, description, next_index)`` for the directive at ``lines[i]``."""
    kind, member = _MEMBER_DIRECTIVE.match(lines[i]).groups()
    description = []
    i += 1
    while i < len(lines) and (not lines[i].strip() or lines[i].startswith("   ")):
        text = lines[i].strip()
        if text and not text.startswith(":"):  # skip directive options such as ``:type:``
            description.append(text)
        i += 1
    return kind, member.strip(), " ".join(description), i


def summarize_member_sections(app, what, name, obj, options, lines):
    if what != "class":
        return
    out = []
    i = 0
    while i < len(lines):
        if not _MEMBER_DIRECTIVE.match(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        kind = _MEMBER_DIRECTIVE.match(lines[i]).group(1)
        title, role = _SUMMARY_TITLES[kind]
        out += [f".. rubric:: {title}", "", ".. list-table::", "   :widths: 30 70", "   :class: pyaml-member-summary", ""]
        while i < len(lines) and (m := _MEMBER_DIRECTIVE.match(lines[i])) and m.group(1) == kind:
            _, member, description, i = _read_member_block(lines, i)
            out += [f"   * - :py:{role}:`~{name}.{member}`", f"     - {description}"]
        out.append("")
    lines[:] = out


def setup(app):
    # Run after napoleon (default priority 500), which produces the member directives.
    app.connect("autodoc-process-docstring", summarize_member_sections, priority=600)


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_title = "pyaml"
html_show_sourcelink = False
html_css_files = ["custom.css"]
html_logo = "_static/_logo/pyaml-logo.svg"

html_theme_options = {
    "navigation_depth": 4,
    "show_nav_level": 2,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/python-accelerator-middle-layer/pyaml",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
    ],
}

html_sidebars = {
    "**": [
        "sidebar-collapse",
        "sidebar-nav-bs",
    ],
}
