# Reference fixtures

The Julia reference assertions under `reference/julia/` are ported from the
`test/` suite of `SebastianManriqueM/TL_parameter_computation`, using the
preserved workbook at `data/raw/Tower_geometries_DB.xlsx` and normalized
catalog at `data/catalog/v1`.

The reference test source is documented in
`plans/existing_julia_code/tl_parameter_computation_map.md`. Geometry and
conductor assertions retain the source tolerances (0.25%, 0.5%, and 0.8%);
electrical matrix assertions retain 0.5% for series matrices and 2.8% for the
shunt matrix. Runtime units follow the Julia parity contract: feet, inches,
ohm/kft, ohm/mile, microsiemens/mile, kV, and MW.
