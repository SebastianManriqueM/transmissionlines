Repository layout
=================

The repository separates installable Python code, tests, source data,
documentation, and development tooling. The following map focuses on
maintained inputs; build products and local environments are not source files.

.. code-block:: text

   .github/
     agents/                 Repository-specific coding agents
     skills/                 Repository-specific development workflows
     workflows/              CI for tests and documentation
   data/
     catalog/v1/             Normalized, versioned Parquet catalog and manifest
     raw/                    Preserved source workbook
   docs/
     source/                 Sphinx documentation source
   plans/                    Local planning notes; excluded from version control
   references/               Reserved for external/source reference material
   scripts/
     build_reference_catalog.py
   src/transmissionlines/    Installable Python package
   test/                     Pytest suite and reference fixtures
   pyproject.toml            Package metadata, dependencies, and tool settings
   uv.lock                   Locked development and documentation dependencies

Python package
--------------

The package is installed from ``src/``. Its modules are organized by the
responsibility that owns each change:

* ``api.py`` is the public convenience facade, collecting supported builders,
  calculations, catalog access, models, and plotting functions.
* ``models/`` defines the typed domain models for cables, geometry,
  configurations, electrical and mechanical parameters, routes, and St. Clair
  results.
* ``catalog/`` imports source data, defines catalog schemas, validates
  manifests and tables, selects catalog records, and provides repository access.
* ``builders/`` turns catalog selections and user inputs into line and system
  model instances.
* ``calculations/`` contains domain computations for cable properties,
  geometry, electrical parameters and matrices, and St. Clair curves.
* ``cli/`` defines the ``tl`` command-line application. The command is
  registered in ``pyproject.toml`` under ``[project.scripts]``.
* ``plotting/`` renders calculated results, such as St. Clair curves.
* ``system.py`` defines the Infrasys-backed system and schema-version handling;
  ``units.py``, ``bundle.py``, and ``exceptions.py`` hold shared unit,
  bundle, and error behavior.
* ``io/`` and ``operations/`` are reserved package boundaries. They currently
  contain only package initializers, so new serialization adapters or
  higher-level operations should be added there only when implemented.

Data, references, and scripts
-----------------------------

* ``data/raw/`` preserves the original ``Tower_geometries_DB.xlsx`` workbook.
  Calculation modules consume the normalized catalog rather than reading this
  workbook directly.
* ``data/catalog/v1/`` contains the normalized Parquet tables and manifest.
  The manifest records provenance and schemas; catalog import and validation
  behavior lives in ``transmissionlines.catalog``.
* ``scripts/build_reference_catalog.py`` regenerates the normalized catalog
  from the preserved workbook. Review the catalog README before regenerating
  committed data.
* ``test/reference/`` contains reviewed fixtures used to compare Python
  results with the original Julia implementation. ``references/`` is a
  separate top-level placeholder for source or external reference material; it
  is not the pytest fixture directory.
* ``plans/`` contains implementation and migration notes used during
  development. It is ignored by Git in this repository and is not part of the
  installed package or the published Sphinx navigation.

Tests and documentation
-----------------------

* ``test/builders/``, ``test/calculations/``, ``test/models/``, and
  ``test/cli/`` cover their corresponding package layers. ``test/integration/``
  checks behavior across layer boundaries, while ``test/reference/`` holds
  reference-based checks and fixtures, and ``test/docs/`` exercises documented
  examples. The test suite is configured in ``pyproject.toml`` and runs with
  ``uv run pytest``.
* ``docs/source/`` is the Sphinx source tree. It is divided into concepts,
  user and developer guides, and generated API-reference pages. The Sphinx
  configuration is in ``docs/source/conf.py``.
* ``.github/workflows/tests.yml`` runs pytest across supported CI operating
  systems. ``.github/workflows/docs.yml`` installs the locked docs group,
  builds HTML with warnings treated as errors, runs doctests, and uploads the
  HTML artifact.

Project configuration and generated files
------------------------------------------

``pyproject.toml`` is the source of truth for package metadata, runtime and
development dependencies, the ``tl`` entry point, and pytest, Ruff, coverage,
and mypy settings. ``uv.lock`` pins the resolved dependency set used by local
development and CI.

Sphinx output is written to ``docs/build/`` and is ignored by Git. Pytest and
coverage can also create local caches, bytecode, and coverage reports; these
are generated artifacts, not documentation or package source. Edit the source
under ``docs/source/`` or ``src/`` rather than files under build-output
directories.