# Electrical parity and reference catalog

This document describes the implemented Julia-parity path and the normalized
catalog artifacts used by the parity tests. Calculations consume validated
runtime models; only the catalog builder reads the preserved workbook.

## Workbook to runtime catalog

```mermaid
flowchart TD
    Workbook[Julia workbook] --> Raw[Preserved raw artifact]
    Raw --> Normalize[Normalize legacy sheets]
    Normalize --> Validate{Records valid}
    Validate -->|no| Reject[Reject catalog]
    Validate -->|yes| Parquet[Write versioned Parquet tables]
    Parquet --> Manifest[Write checksum manifest]
    Parquet --> Repository[Exact catalog repository]
    Repository --> Builder[Build runtime specifications]
    Builder --> Provenance[Attach catalog references]
```

The generated `data/catalog/v1` tables are:

| Table | Runtime meaning | Important units |
| --- | --- | --- |
| `tower_geometries` | Structure identity and topology | kV, circuit and wire counts |
| `phase_positions` | Circuit phase coordinates | feet |
| `ground_wire_positions` | Ground-wire coordinates | feet |
| `conductors` | Phase conductor electrical source fields | inches, ohm/kft, Mohm/kft |
| `ground_wires` | Ground-wire source fields | inches, ohm/kft |
| `states`, `state_borders` | Exact state identity and adjacency | identifiers |
| `actual_lines` | Preserved workbook line records | source units |

## Electrical calculation algorithm

```mermaid
flowchart TD
    Inputs[Validated geometry and cable specifications] --> Order[Order phases and ground wires]
    Order --> Units[Convert to Julia parity units]
    Units --> Distances[Calculate direct and image distances]
    Units --> Bundles[Derive GMR and equivalent radius]
    Distances --> PrimitiveZ[Build primitive series Z]
    Bundles --> PrimitiveZ
    Distances --> PrimitiveP[Build primitive potential P]
    Bundles --> PrimitiveP
    PrimitiveZ --> KronZ[Kron reduce ground block]
    PrimitiveP --> KronP[Kron reduce ground block]
    KronP --> Admittance[Build shunt admittance Y]
    KronZ --> TransposeZ[Apply full transposition]
    Admittance --> TransposeY[Apply full transposition]
    TransposeZ --> SequenceZ[Transform to sequence Z]
    TransposeY --> SequenceY[Transform to sequence Y]
    SequenceZ --> Scalars[Extract sequence scalars]
    SequenceY --> Scalars
    Scalars --> Results[JSON safe ElectricalParameters]
```

### Optional parity capacitance radius

`BareConductorEquipment.capacitance_radius` is an optional parity-only field.
The catalog builder derives it from `C_60Hz_Mohm_kft` using the Julia
capacitance-radius equation. It is not a user override and is absent when the
source field is unavailable. Bundle derivation prefers this radius for the
potential matrix and falls back to physical conductor diameter for general
runtime data. Ground wires remain unbundled and use their physical radius.

The parity contract is retained at the calculation boundary:

- coordinates, distances, GMR, and equivalent radius: feet;
- bundle spacing and diameter: inches;
- resistance input: ohm/kft;
- series impedance: ohm/mile;
- shunt admittance: microsiemens/mile;
- voltage: kV; and
- SIL: MW.

The implementation retains the Julia constants `R_CONST = 0.00158836`,
`L_CONST = 0.00202237`, `L_FACTOR = 7.6786`, and
`EPSILON_AIR = 1.4240e-2`, including the Julia frequency and mile/kft factors.

## Runtime ownership

```mermaid
classDiagram
    class CatalogRepository {
        exact selection
        read Parquet only
    }
    class LineBuilder {
        convert records
        attach provenance
    }
    class TowerGeometry {
        phase positions
        ground positions
    }
    class PhaseConductorSpec {
        circuit id
        bundle count
        derived GMR
        derived radius
    }
    class GroundWireSpec {
        shared unbundled cable
    }
    class ElectricalParameters {
        matrices
        sequence scalars
        units and provenance
    }
    class GeometryCalculations {
        pure transformations
    }
    class CableCalculations {
        pure transformations
    }
    class MatrixCalculations {
        pure transformations
    }
    class ElectricalCalculations {
        orchestration
    }
    CatalogRepository --> LineBuilder : selected records
    LineBuilder --> TowerGeometry : creates
    LineBuilder --> PhaseConductorSpec : creates
    LineBuilder --> GroundWireSpec : creates
    TowerGeometry --> ElectricalCalculations : input
    PhaseConductorSpec --> ElectricalCalculations : input
    GroundWireSpec --> ElectricalCalculations : input
    GeometryCalculations --> ElectricalCalculations : distances
    CableCalculations --> ElectricalCalculations : cable values
    MatrixCalculations --> ElectricalCalculations : matrix stages
    ElectricalCalculations --> ElectricalParameters : creates
```

Calculation modules do not read workbook or Parquet files and do not mutate
components. Catalog access and runtime-model construction remain in the
catalog and builder layers respectively.
