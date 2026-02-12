# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import sys
# sys.path.insert(0, os.path.abspath('.'))
# sys.path.insert(0, os.path.abspath('../pyat'))
# print(sys.path)

import pyaml

# Generate reference API
from pyaml.apidoc.gen_api import gen_doc

gen_doc()

# -- Project information -----------------------------------------------------

project = "Python Accelerator Middle Layer"
project_copyright = "2024, pyAML Collaboration"
author = "pyAML Collaboration"

# The full version, including alpha/beta/rc tags
release = ".".join(pyaml.__version__.split(".")[:3])
version = ".".join(pyaml.__version__.split(".")[:2])

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

root_doc = "index"
extensions = [
    "sphinx.ext.autosummary",  # Automatically generates summary tables and stub pages
    # for documented functions, classes, and modules
    "sphinx.ext.napoleon",  # Adds support for NumPy-style and Google-style docstrings,
    # so you don’t have to write reStructuredText by hand.
    "sphinx.ext.autodoc",  # Adds support for NumPy-style and Google-style docstrings
    # code snippets.
    "sphinx.ext.intersphinx",  # Allows you to link to documentation of other projects
    # (e.g. NumPy, Python, SciPy) as if they were local.
    "sphinx.ext.githubpages",  # Adds support files (like .nojekyll) needed to publish
    # docs on GitHub Pages.
    "sphinx.ext.viewcode",  # Adds links in the docs to view the source code of
    # documented Python objects.
    "myst_nb",  # Enables MyST Markdown and Jupyter Notebook support.
    "sphinx_copybutton",  # Adds a “copy to clipboard” button to code blocks.
    "sphinx_design",  # Provides layout and design components
    # (cards, grids, tabs, buttons).
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["README.rst", "**/*.so", "_build/*"]

# Injects content at the top of every reStructuredText file before it’s parsed.
# Defines a custom inline role called :pycode: which renders inline code with Python
# syntax highlighting
rst_prolog = """
.. role:: pycode(code)
   :language: python
"""

autodoc_default_options = {
    # Make sure that any autodoc declarations show the right members
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "groupwise",
}
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"
autodoc_typehints_format = "short"
autosummary_generate = True  # Make _autosummary files and include them
autosummary_generate_overwrite = False
autosummary_ignore_module_all = False
autoclass_content = "both"  # include both class docstring and __init__

napoleon_use_rtype = False  # More legible
# napoleon_numpy_docstring = False  # Force consistency, leave only Google
napoleon_custom_sections = [("Returns", "params_style")]

add_module_names = False

# -- Options for the myst markdown parser ------------------------------------

myst_enable_extensions = [
    "attrs_inline",
    "colon_fence",
    "dollarmath",
    "replacements",
    "deflist",
]
myst_heading_anchors = 3
nb_execution_mode = "auto"
nb_execution_allow_errors = True

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'alabaster'
# html_theme = 'sphinx_rtd_theme'
# html_theme = 'sphinx_book_theme'
html_theme = "pydata_sphinx_theme"
html_logo = "_static/img/logo.png"
html_copy_source = False
html_theme_options = {
    "github_url": "https://github.com/python-accelerator-middle-layer/pyaml",
    "logo": {
        "image_light": "_static/img/logo.png",
        "image_dark": "_static/img/dark.png",
    },
}
html_sidebars = {
    "index": [],
    "common/about": [],
}
# creates an additional page, but impossible to link to it...
# if os.environ.get('READTHEDOCS') == 'True':
#     html_additional_pages = {
#         "index": "plink.html"
# }

html_css_files = ["css/custom.css"]

# Add any paths that contaAddedin custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# -- Options for latex output -------------------------------------------------

# latex_documents = [
#     (
#         "p/index",
#         "pyat.tex",
#         "PyAT User's Guide",
#         "The AT collaboration",
#         "manual",
#         True,
#     ),
#     (
#         "common/passmethods",
#         "at.tex",
#         "AT Integrators",
#         "The AT collaboration",
#         "manual",
#         False,
#     ),
# ]
# latex_logo = "images/ATlarge.png"

latex_documents = [
    (root_doc, "pyaml.tex", "pyAML Documentation", "pyAML collaboration", "manual"),
]

# -- Options for copybutton  -------------------------------------------------

copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = True

# extensions = [
#     "sphinx.ext.autodoc",
#     "sphinx.ext.doctest",
#     "sphinx.ext.todo",
#     "sphinx.ext.coverage",
#     "sphinx.ext.mathjax",
#     "sphinx.ext.viewcode",
#     "sphinx.ext.githubpages",
#     "sphinx.ext.napoleon",
#     "sphinx.ext.autosectionlabel",
#     "sphinx.ext.autosummary",
#     "myst_nb",
# ]
# autosectionlabel_prefix_document = True
# autosectionlabel_maxdepth = 2

# # Add any paths that contain templates here, relative to this directory.
# # templates_path = ['_templates']

# # The suffix(es) of source filenames.
# # You can specify multiple suffix as a list of string:
# #
# # source_suffix = ['.rst', '.md']
# source_suffix = ".rst"

# # The master toctree document.
# master_doc = "index"


# # The language for content autogenerated by Sphinx. Refer to documentation
# # for a list of supported languages.
# #
# # This is also used if you do content translation via gettext catalogs.
# # Usually you set "language" from the command line for these cases.
# language = "en"

# # List of patterns, relative to source directory, that match files and
# # directories to ignore when looking for source files.
# # This patterns also effect to html_static_path and html_extra_path
# exclude_patterns = []

# # The name of the Pygments (syntax highlighting) style to use.
# pygments_style = "sphinx"

# # If true, `todo` and `todoList` produce output, else they produce nothing.
# todo_include_todos = True

# # -- Options for HTML output ----------------------------------------------

# # The theme to use for HTML and HTML Help pages.  See the documentation for
# # a list of builtin themes.
# #

# # html_theme = 'classic'
# html_theme = "pydata_sphinx_theme"

# # Theme options are theme-specific and customize the look and feel of a theme
# # further.  For a list of options available for each theme, see the
# # documentation.


# # Name of an image file (path relative to the configuration directory)
# # that is the logo of the docs, or URL that points an image file for the logo.
# # It is placed at the top of the sidebar;
# # its width should therefore not exceed 200 pixels.
# html_logo = "_static/img/logo.png"
# html_copy_source = False

# html_theme_options = {
#     "collapse_navigation": False,
#     "display_version": True,
#     "logo_only": True,
#     "navigation_depth": 6,
#     "rightsidebar": True,
#     "relbarbgcolor": "black",
#     "github_url": "https://github.com/python-accelerator-middle-layer/pyaml",
#     "logo": {
#         "image_light": "_static/img/logo.png",
#         "image_dark": "_static/img/dark.png",
#     },
# }

# # Add any paths that contain custom static files (such as style sheets) here,
# # relative to this directory. They are copied after the builtin static files,
# # so a file named "default.css" will overwrite the builtin "default.css".
# #
# html_static_path = ["_static"]

# # A dictionary of values to pass into the template engine’s context for all
# # pages. Single values can also be put in this dictionary using the
# # -A command-line option of sphinx-build.
# html_context = {
#     "display_github": True,
#     # the following are only needed if :github_url: is not set
#     "github_user": author,
#     "github_repo": project,
#     "github_version": "main/docs/",
# }

# # A list of CSS files. The entry must be a filename string or a tuple
# # containing the filename string and the attributes dictionary.
# # The filename must be relative to the html_static_path, or a full URI with
# # scheme like https://example.org/style.css.
# # The attributes is used for attributes of <link> tag.
# # It defaults to an empty list.
# #
# html_css_files = ["css/custom.css"]

# smartquotes_action = (
#     "qe"  # renders only quotes and ellipses (...) but not dashes (option: D)
# )

# # Custom sidebar templates, must be a dictionary that maps document names
# # to template names.
# #
# # This is required for the alabaster theme
# # refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
# html_sidebars = {
#     "**": [
#         "relations.html",  # needs 'show_related': True theme option to display
#         "searchbox.html",
#     ],
#     "index": [],
#     "common/about": [],
# }


# # -- Options for HTMLHelp output ------------------------------------------

# # Output file base name for HTML help builder.
# htmlhelp_basename = "pyamldoc"

# # -- Options for LaTeX output ---------------------------------------------

# latex_elements = {
#     # The paper size ('letterpaper' or 'a4paper').
#     #
#     # 'papersize': 'letterpaper',
#     # The font size ('10pt', '11pt' or '12pt').
#     #
#     # 'pointsize': '10pt',
#     # Additional stuff for the LaTeX preamble.
#     #
#     # 'preamble': '',
#     # Latex figure (float) alignment
#     #
#     # 'figure_align': 'htbp',
# }

# # Grouping the document tree into LaTeX files. List of tuples
# # (source start file, target name, title,
# #  author, documentclass [howto, manual, or own class]).
# latex_documents = [
#     (master_doc, "pyaml.tex", "pyAML Documentation", "pyAML collaboration", "manual"),
# ]

# # -- Options for manual page output ---------------------------------------

# # One entry per manual page. List of tuples
# # (source start file, name, description, authors, manual section).
# man_pages = [(master_doc, "pyaml", "pyAML Documentation", [author], 1)]

# # -- Options for Texinfo output -------------------------------------------

# # Grouping the document tree into Texinfo files. List of tuples
# # (source start file, target name, title, author,
# #  dir menu entry, description, category)
# texinfo_documents = [
#     (
#         master_doc,
#         "pyaml",
#         "pyAML Documentation",
#         author,
#         "pyaml",
#         "One line description of project.",
#         "Miscellaneous",
#     ),
# ]

# # -- Autodoc Configuration ---------------------------------------------------

# # Add here all modules to be mocked up. When the dependencies are not met
# # at building time. Here used to have PyQT mocked.
# autodoc_mock_imports = [
#     "PyQt5",
#     "PyQt5.QtGui",
#     "PyQt5.QtCore",
#     "PyQt5.QtWidgets",
#     "matplotlib.backends.backend_qt5agg",
# ]

# # -- Options for the myst markdown parser ------------------------------------

# myst_enable_extensions = [
#     "attrs_inline",
#     "colon_fence",
#     "dollarmath",
#     "replacements",
#     "deflist",
# ]
# myst_heading_anchors = 3
# nb_execution_mode = "off"  # "auto"
# nb_execution_allow_errors = True
