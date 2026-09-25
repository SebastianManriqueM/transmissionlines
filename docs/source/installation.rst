Installation
============

Requirements
------------

The package requires Python 3.12 or newer. It is not released to PyPI; install
from a repository checkout. The project uses `uv <https://docs.astral.sh/uv/>`_
and the checked-in ``uv.lock`` to reproduce its development environment.

Development environment
-----------------------

From the repository root, install the locked project and development tools:

.. code-block:: console

   uv sync --locked

To install Sphinx for a local documentation build:

.. code-block:: console

   uv sync --locked --group docs
   uv run sphinx-build -W --keep-going -b html docs/source docs/build/html

The HTML site is written to ``docs/build/html/index.html``. Run the executable
documentation examples with:

.. code-block:: console

   uv run sphinx-build -W --keep-going -b doctest docs/source docs/build/doctest

Verify package and command entry-point imports with:

.. code-block:: console

   uv run python -c "import transmissionlines; print(transmissionlines.SCHEMA_VERSION)"
   uv run tl --help

The current ``tl`` entry point is a placeholder and has no implemented command
set; the second command only checks that the installed console entry point
launches. Do not rely on it for catalog or calculation workflows yet.