For Users New to Python
========================

If you are a new Python user this page provides some help to get started. It also provides some advice for MATLAB users migrating to Python.

Python is a large ecosystem with many tools to achieve similar things so this is not intended to be a complete list. Which tool to use is often based on personal preference and the intention of this guide is only to provide a starting point for you to find you preferred setup.


Integrated Development Environments
-----------------------------------------

Python can be run directly in a terminal or an [IPython](https://ipython.org/) shell but if you want to do more complex things like debug or develop code it is easier to use an Integrated Development Environment (IDE). There are many IDEs with Python support with different features, user experience etc so the choice of IDE is highly personal. Three common ones to use are:

- **Spyder**:
    [https://www.spyder-ide.org/](https://www.spyder-ide.org/) 

    Spyder is designed for scientific computing and data analysis. It has the most MATLAB-like interface which often makes it a preferred choice among MATLAB users who want to migrate to Python. It works well when using standard scientific Python packages but has currently less support for custom Python classes. It also only has basic Git integration and works best with conda environments. There is an plugin for Jupyter notebooks but it is not available for all the installation options yet.
    
- **VS Code**
    [https://code.visualstudio.com/](https://code.visualstudio.com/)

    VS Code supports Python through extensions. It also has extensions for other programming languages as well as Jupyter notebooks. It has a very good Git integration making it a good choice if you are new to using version control and prefer to not use the terminal. It also has very good support for all type of virtual environments. In addition to this it has extensions to connect to remote services (such as clusters) and JupyterHubs in case you want to run on an external resource and many HPC centers therefore now provide a web-based version for their users. It however makes heavy use of keyboard shortcuts which can be a bit of a learning curve for new users.

- **PyCharm**

    [https://www.jetbrains.com/pycharm/](https://www.jetbrains.com/pycharm/)

    PyCharm is a dedicated Python IDE. It has many features and customization possibilities and is therefore often used by software professionals. There is both a community (free) and professional (paid) edition.

If you are a new user getting started who doesn't know yet what you prefer, a good choice is likely to start with VS Code.


Jupyter Notebooks
-----------------
[https://jupyter.org/](https://jupyter.org/)

A very common way to run Python in science is to use Jupyter notebooks. Is a browser-based tool which is very useful for data visualisation and interactive work. It can be installed both in a basic version with notebooks or as JupyterLab which also provides some useful IDE features. Many tutorials will come in the form of a notebook.


Installing Python
-----------------

There are many different ways to get an installation of Python. An important aspect is that you at some point might need to be able to switch between different versions and have more than one version installed simultaneously. There are different options available for this and here are some common ones:

- **pyenv**
    [https://github.com/pyenv/pyenv](https://github.com/pyenv/pyenv)

    This is the most basic choice but probably too basic for most users. There is a plugin [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) if you also want the tool to manage virtual environments.

- **conda**
    [https://docs.conda.io/projects/conda/en/stable/][https://docs.conda.io/projects/conda/en/stable/]

    Conda is often used in the scientific community. There are several versions available and some might require a license. A good choice to avoid license issues is to choose [miniforge](https://github.com/conda-forge/miniforge). This gives you a minimal installation of the free community edition. In addition to different Python versions, it also provides an easy way to manage and create virtual environments.

- **uv**
    [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

    Uv is a new tool which is intended as a single tool to replace the functionality of many other tools. In addition to managing Python versions and virtual environments it can also help to build packages. It however has a bit of a learning curve so is likely mostly a good choice for the experienced user who also want to do development work.
    

Python Packages
----------------- 

After you have installed Python you need to install packages for the code that you want to use. There are two common ways to do this:

- **pip**
    [https://pip.pypa.io/en/stable/](https://pip.pypa.io/en/stable/)

    Pip is the standard package installer for Python. It is often automatically installed when you install Python and is easy to use. You can install from different sources as explained in the documentation [https://pip.pypa.io/en/stable/getting-started/](https://pip.pypa.io/en/stable/getting-started/).

- **conda**

    If you are using conda, it also provides its own way of installing packages. You can however still use pip in conda environments in case the package is not available as a conda package. The installation is similar to when using pip [https://www.anaconda.com/docs/getting-started/working-with-conda/packages/install-packages][https://www.anaconda.com/docs/getting-started/working-with-conda/packages/install-packages].


Virtual Environments
--------------------

A key aspect of a good Python setup is to use virtual environments. A virtual environment is a self-contained directory which contains a Python installation for a particular Python version plus additional packages. The purpose is to be able to install packages without fear of compatibility issues which might cause your entire Python setup to break. If something goes wrong, you can just delete the virtual environment and start over.

**You should never install Python packages in your default Python environment. It can cause big problems and especially if your computer is using an OS which also relies on Python."

The recommended workflow is to always create a virtual environment, activate it and then install the Python packages you need into it. There are two different versions of virtual environments:

- **venv**
    [https://docs.python.org/3/library/venv.html][https://docs.python.org/3/library/venv.html]

    This is the standard way which comes with the Python installation. It is very lightweight but can sometimes be annoying to use because you need to remember the command to activate the environment after it was created. The virtual environment is also created in the current working folder so there is no global way to manage your environments if you want an easy way to switch between environments. However, tools exist to extend the functionality such as [virtualenv](https://virtualenv.pypa.io/en/latest/) and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/).

- **conda**
    Conda can also create virtual environments. It provides and easy way to activate and switch between environments so is a good choice for new users.

Some IDEs has the functionality to help you create and switch between virtual environments. This works for both type of environments and can substantially simplify the workflow compared to using the terminal.


Example Resources
------------------

There are many resources available for learning Python and also dedicated resources tailored for the scientific community. Several organisations also provide free courses and material for scientists. Here are some recommendations:

- **The Python documentation**: [https://www.python.org/](https://www.python.org/)
- **Python Packaging User Guide**: [https://packaging.python.org/en/latest/](https://packaging.python.org/en/latest/)
- **Scientific Python**: [https://scientific-python.org/](https://scientific-python.org/)
- **Carpentries**: [https://carpentries.org/](https://carpentries.org/)
- **CodeRefinery**: [https://coderefinery.org/](https://coderefinery.org/)
- **Software Sustainability Institute.**: [https://www.software.ac.uk/](https://www.software.ac.uk/)
