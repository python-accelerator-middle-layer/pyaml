# -*- coding: utf-8 -*-
#
# pyAML documentation build configuration file, originally created for pySC: https://github.com/lmalina/pySC/blob/master/doc/conf.py
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import pathlib
import sys
# ignore numpy warnings, see:
# https://stackoverflow.com/questions/40845304/runtimewarning-numpy-dtype-size-changed-may-indicate-binary-incompatibility
import warnings

warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")


TOPLEVEL_DIR = pathlib.Path(__file__).parent.parent.absolute()
ABOUT_FILE = TOPLEVEL_DIR / "pyAML" / "__init__.py"

if str(TOPLEVEL_DIR) not in sys.path:
    sys.path.insert(0, str(TOPLEVEL_DIR))

ABOUT_PYAML: dict = {}
with ABOUT_FILE.open("r") as f:
    exec(f.read(), ABOUT_PYAML)

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.doctest',
              'sphinx.ext.todo',
              'sphinx.ext.coverage',
              'sphinx.ext.mathjax',
              'sphinx.ext.viewcode',
              'sphinx.ext.githubpages',
              'sphinx.ext.napoleon',
              'sphinx.ext.autosectionlabel',
              ]
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 2

# Add any paths that contain templates here, relative to this directory.
# templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = ABOUT_PYAML["__title__"]
copyright_ = '2024, pyAML collaboration'
author = ABOUT_PYAML["__author__"]

rst_prolog = f"""
:github_url: {ABOUT_PYAML['__url__']}
"""

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ABOUT_PYAML["__version__"][:3]
# The full version, including alpha/beta/rc tags.
release = ABOUT_PYAML["__version__"]

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'classic'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'collapse_navigation': False,
    'display_version': True,
    'logo_only': True,
    'navigation_depth': 2,
}


# Name of an image file (path relative to the configuration directory)
# that is the logo of the docs, or URL that points an image file for the logo.
# It is placed at the top of the sidebar;
# its width should therefore not exceed 200 pixels.
html_logo = '_static/img/logo.png'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#
html_static_path = ['_static']

# A dictionary of values to pass into the template engine’s context for all
# pages. Single values can also be put in this dictionary using the
# -A command-line option of sphinx-build.
html_context = {
    'display_github': True,
    # the following are only needed if :github_url: is not set
    'github_user': author,
    'github_repo': project,
    'github_version': 'main/docs/',
}

# A list of CSS files. The entry must be a filename string or a tuple
# containing the filename string and the attributes dictionary.
# The filename must be relative to the html_static_path, or a full URI with
# scheme like https://example.org/style.css.
# The attributes is used for attributes of <link> tag.
# It defaults to an empty list.
#
html_css_files = ["css/custom.css"]

smartquotes_action = "qe"  # renders only quotes and ellipses (...) but not dashes (option: D)

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
html_sidebars = {
    '**': [
        'relations.html',  # needs 'show_related': True theme option to display
        'searchbox.html',
    ]
}

# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'pyamldoc'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'pyaml.tex', u'pyAML Documentation',
     u'pyAML collaboration', 'manual'),
]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'pyaml', u'pyAML Documentation',
     [author], 1)
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'pyaml', u'pyAML Documentation',
     author, 'pyaml', 'One line description of project.',
     'Miscellaneous'),
]

# -- Autodoc Configuration ---------------------------------------------------

# Add here all modules to be mocked up. When the dependencies are not met
# at building time. Here used to have PyQT mocked.
autodoc_mock_imports = ['PyQt5', 'PyQt5.QtGui', 'PyQt5.QtCore', 'PyQt5.QtWidgets',
                        "matplotlib.backends.backend_qt5agg",
                        ]