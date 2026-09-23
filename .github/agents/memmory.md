# Python Code Implementer Memory

Record only durable, repository-specific learnings after completed tasks.

## Learnings

- No verified learnings recorded yet.
- 2026-09-22: The sibling `TL_parameter_computation` repository is an include-based Julia codebase; include `src/TransmissionLineParameters.jl` from its repository root. Its focused suite entry point is `test/runtests.jl`, which loads `src/data/Tower_geometries_DB.xlsx` through a repository-relative path.
- 2026-09-22: The approved Python migration architecture uses `infrasys` for serializable transmission-line component graphs and Pint quantities; normalized versioned Parquet catalogs remain outside the component system. The detailed migration plan is `plans/migration_plan/python_migration_plan.md`.