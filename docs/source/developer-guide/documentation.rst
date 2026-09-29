Documentation development
=========================

The Sphinx source uses the separated layout under ``docs/source`` and writes
generated files under the ignored ``docs/build`` directory. Pages use
reStructuredText, NumPy-style Python docstrings, autodoc, autosummary, and
MathJax. The site uses the Read the Docs theme (``sphinx_rtd_theme``).
Existing repository notes at ``docs/catalog_v3.md``,
``docs/electrical_parity_and_catalog.md``, and
``docs/infrasys_foundation_notes.md`` remain in place; their maintained content
is reflected in the catalog, equations, data-model, and serialization pages.

Build HTML with warnings as errors and execute interactive examples with the
Sphinx doctest builder:

.. code-block:: console

   uv sync --locked --group docs
   uv run sphinx-build -W --keep-going -b html docs/source docs/build/html
   uv run sphinx-build -W --keep-going -b doctest docs/source docs/build/doctest

When documenting a public symbol, check its actual signature and nearest tests.
Add a NumPy-style docstring to public APIs whose parameter, return, error, or
example behavior is not clear from the current docstring. Add pages to the
nearest nested toctree. Keep generic examples independent of local catalog
files; catalog-specific recipes can use the bundled ``data/catalog/v1``
snapshot and should run from the repository root.

Review equations against ``plans/existing_julia_code/tl_parameter_computation_map.md``,
``plans/st Clair curve/st clair model.md``, and
``plans/st Clair curve/st_clair_curve_implementation_plan.md``. Treat Python
source and tests as the executable authority. Record any plan/code disagreement
in this guide or the implementation summary; do not silently substitute a
textbook equation for a parity-specific implementation.