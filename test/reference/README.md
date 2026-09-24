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

## Two-circuit reference case

`julia/two_circuit_3l11_cardinal.json` is the reviewed two-circuit case used
by `calculations/test_electrical_parity.py`:

- original source row: `examples/tl_designs_with_parameters_2circuits.csv`,
  345 kV `3L11`, case `S`, Cardinal, two circuits;
- geometry: workbook/catalog structure `3L11`, with two phase circuits and
  two ground wires;
- phase conductors: ACSR Cardinal, one specification per circuit, two
  subconductors at 18 inches;
- ground wire: Alumoweld `7/8`, shared by both ground-wire positions;
- technical inputs: 345 kV, 60 Hz, and 100 ohm-meter earth resistivity;
- source scalar cross-check: the original CSV reports
  `r1=0.06041707268316814`, `x1=0.571814216468555`,
  `b1=7.540921284378496`, and `sil=432.2379746677453 MW`;
- tolerance: 0.5% for series/scalar values and 2.8% for shunt values,
  matching the active Julia shunt tolerance and the existing parity tests.

The fixture stores the canonical JSON-safe matrices, labels, units, scalar
units, topology, and catalog provenance. Matrix values are generated from the
Julia equations and independently anchored by the original CSV scalar row;
no formatted matrix strings or NumPy complex values are stored.
