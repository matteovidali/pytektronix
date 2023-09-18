# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'PyTektronix'
copyright = '2023, Matteo Vidali'
author = 'Matteo Vidali'
release = '1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import sphinx_rtd_theme
import sys
sys.path.append("../src/")
extensions = [
        "sphinx_rtd_theme",
        "sphinx.ext.autodoc"
]

autodoc_mock_imports = [
    "numpy",
    "aenum",
    "pytest", 
    "pyVISA-py",
    "pyVISA",
    "pyvisa",
    "typing_extensions",
    "vxi11",
    "python-vxi11",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

def skip(app, what, name, obj, would_skip, options):
    if name == "__init__":
        return False
    return would_skip

def setup(app):
    app.connect("autodoc-skip-member", skip)
