# Python Code Implementer Memory

Record only durable, repository-specific learnings after completed tasks.

## Learnings

- No verified learnings recorded yet.
- 2026-09-22: The sibling `TL_parameter_computation` repository is an include-based Julia codebase; include `src/TransmissionLineParameters.jl` from its repository root. Its focused suite entry point is `test/runtests.jl`, which loads `src/data/Tower_geometries_DB.xlsx` through a repository-relative path.
- 2026-09-22: The approved Python migration architecture uses `infrasys` for serializable transmission-line component graphs and Pint quantities; normalized versioned Parquet catalogs remain outside the component system. The detailed migration plan is `plans/migration_plan/python_migration_plan.md`.
- 2026-09-25: Electrical positive-sequence scalar maps use actual `TowerGeometry` circuit IDs, preserving unambiguous joins to conductor specs. Line-level St. Clair results attach by copying `TransmissionLine` and `ElectricalParameters`; validate with `.venv\Scripts\python.exe -m pytest test -q`.
- 2026-09-25: Direct St. Clair inputs require conductor ampacity (accept `conductor_ampacity_a` or `ampacity_a`); the angle grid appends and evaluates the exact configured stability limit when the step does not divide it. Keep `.coverage` and `__pycache__` out of the worktree; retain the example plot only while documentation references it.
- 2026-09-25: The `3L11` electrical parity fixture uses two Cardinal ACSR circuits, each with two subconductors at 18-inch spacing; the v1 catalog rating is 990 A per subconductor. Its calculated first-circuit positive-sequence constants are `r1=0.06041707268316814` ohm/mile, `x1=0.571814216468555` ohm/mile, and `b1=7.540921284378496` microsiemens/mile.
- 2026-09-25: `plot_st_clair_curve(show_voltage_limit=True)` adds actual receiving-end voltage profiles and the configured pu voltage threshold on a secondary axis; it does not invent a separate voltage-limited MW curve when the threshold is not reached.
- 2026-09-25: `_solve_mesh` scales per-mile series resistance and reactance, and shunt susceptance, by line length before solving; `test_mesh_power_loss_identity_and_sensitivity_serialization` now checks series-impedance scaling from 20 to 600 miles.
- 2026-09-25: St. Clair Thevenin sources use separate nonnegative `r_system_*_ohm` and positive `x_system_*_ohm` fields; defaults are `0.1 + j1 ohm` on each end, and the mesh solver must retain the full complex source impedances.
- 2026-09-25: Keep ordinary imports at module scope. `models.cables` depends on pure bundle derivations, so those helpers live in cycle-free `transmissionlines.bundle`; `calculations.cable` re-exports them for compatibility. Use deferred imports only for demonstrated cycles or optional dependencies.
- 2026-09-25: Matplotlib is a required project dependency; St. Clair plotting tests import it directly and run with the noninteractive Agg backend rather than skipping when it is absent.