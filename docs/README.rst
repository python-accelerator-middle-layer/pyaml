##################
pyAML Documentation
##################

This directory is the source of the pyAML documentation.

**********************************
Contributing to documentation
**********************************

Documentation tools
===================

The documentation is compiled with
`Sphinx <https://www.sphinx-doc.org/en/master/index.html>`_.

For a local check when writing documentation, Sphinx and the
necessary extensions are automatically installed if you install pyAML with
the [doc] option::

    $ pip install -e ".[doc]"

Then, the compilation may be triggered from the ``docs`` directory with::

    $ cd pyaml/docs
    $ make html

