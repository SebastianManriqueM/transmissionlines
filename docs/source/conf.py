"""Sphinx configuration for the transmissionlines documentation."""

from pathlib import Path
import os
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

with (ROOT / "pyproject.toml").open("rb") as project_file:
    PROJECT_METADATA = tomllib.load(project_file)["project"]

project = PROJECT_METADATA["name"]
author = "TransmissionLines contributors"
release = PROJECT_METADATA["version"]
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinxcontrib.mermaid",
]

autosummary_generate = True
autodoc_typehints = "description"
autodoc_member_order = "bysource"
napoleon_numpy_docstring = True
nitpicky = False
todo_include_todos = False

_intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pydantic": ("https://pydantic.dev/docs/validation/latest", None),
    "infrasys": ("https://natlabrockies.github.io/infrasys", None),
}
intersphinx_mapping = _intersphinx_mapping if os.environ.get("CI") else {}

templates_path = ["_templates"]
exclude_patterns = ["_build", "build", "_autosummary"]
html_theme = "alabaster"
html_static_path = []
html_title = f"{project} {release} documentation"
mermaid_version = "11.12.1"