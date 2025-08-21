# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
from __future__ import annotations

import sys
from importlib.metadata import version as _version
from pathlib import Path

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(str((Path(__file__).parent / "_ext").resolve()))

project = "Django MongoDB Backend"
copyright = "2025, The MongoDB Python Team"
author = "The MongoDB Python Team"
release = _version("django_mongodb_backend")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False
# Disable auto-created table of contents entries for all domain objects
# (functions, classes, attributes, etc.)
toc_object_entries = False

extensions = [
    "djangodocs",
    "sphinx.ext.intersphinx",
]

# templates_path = ["_templates"]
exclude_patterns = []

intersphinx_mapping = {
    "django": (
        "https://docs.djangoproject.com/en/5.2/",
        "https://docs.djangoproject.com/en/5.2/_objects/",
    ),
    "mongodb": ("https://www.mongodb.com/docs/languages/python/django-mongodb/v5.2/", None),
    "pymongo": ("https://pymongo.readthedocs.io/en/stable/", None),
    "python": ("https://docs.python.org/3/", None),
    "atlas": ("https://www.mongodb.com/docs/atlas/", None),
    "manual": ("https://www.mongodb.com/docs/manual/", None),
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
