# Python Code Implementer Memory

Record only durable, repository-specific learnings after completed tasks.

## Learnings

- No verified learnings recorded yet.
- 2026-09-22: The sibling `TL_parameter_computation` repository is an include-based Julia codebase; include `src/TransmissionLineParameters.jl` from its repository root. Its focused suite entry point is `test/runtests.jl`, which loads `src/data/Tower_geometries_DB.xlsx` through a repository-relative path.
- 2026-09-22: The approved Python migration architecture uses `infrasys` for serializable transmission-line component graphs and Pint quantities; normalized versioned Parquet catalogs remain outside the component system. The detailed migration plan is `plans/migration_plan/python_migration_plan.md`.
- 2026-09-23: Phase 0 uses the `src/transmissionlines` package layout with `uv`; verify it with `uv run pytest test -q`, `uv run ruff check src test`, and `uv run mypy src`.
- 2026-09-23: `infrasys 1.2.1` serializes systems to JSON file paths and uses its shared Pint registry. Nested `LineDataModel` quantity strings must be reconstructed as their declared `BaseQuantity` subclass before Pydantic validation.
- 2026-09-23: The `tl` entry point must retain a registered Typer callback so its help command remains runnable while feature commands are added later.
- 2026-09-23: `ComplexMatrix` persisted fields use tuple containers and reject non-finite values to preserve validated shape and JSON round-trip behavior.