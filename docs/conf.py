# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

master_doc = "index"

# -- Project information -----------------------------------------------------

project = "trace-glare"
copyright = "2020, Bruno Bueno"
author = "Bruno Bueno"

# The full version, including alpha/beta/rc tags
release = "0.1"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",  # https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html
    "sphinx.ext.autosummary",  # https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html
    "sphinx.ext.doctest",  # https://www.sphinx-doc.org/en/master/usage/extensions/doctest.html
    "sphinx.ext.intersphinx",  # http://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#module-sphinx.ext.intersphinx
    "sphinx.ext.napoleon",  # https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#module-sphinx.ext.napoleon
    "sphinx.ext.viewcode",  # https://www.sphinx-doc.org/en/master/usage/extensions/viewcode.html
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["html"]

autoclass_content = "both"  # include both class docstring and __init__
autodoc_default_flags = [
    # "inherited-members",
    "members",
    # "private-members",
    "show-inheritance",
    # "special-members",
    "undoc-members",
]
autosummary_generate = True  # Make _autosummary files and include them
napoleon_numpy_docstring = False  # Force consistency, leave only Google
napoleon_use_rtype = False  # More legible

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["static"]