# Infrasys foundation notes for v3

Issue #2 establishes the package/runtime foundation for the v3 transmission-line migration. This note records the Infrasys 1.2.1 serialization behaviors verified by the foundation tests and the modeling constraints they imply for later slices.

## Verified behaviors

### Registered components

Registered `infrasys.Component` subclasses round-trip through `System.to_json()` and `System.from_json()` with UUID identity and required immutable names. Direct component-reference fields on another registered component are serialized as Infrasys component references and resolve back to the registered object during deserialization.

```python
class Bus(Component):
    location: GeographicPoint


class TransmissionLine(Component):
    from_bus: Bus
    to_bus: Bus
```

For this direct-reference shape, a loaded line's `from_bus` and `to_bus` fields are the same system-owned objects returned by `get_component()`.

### Supplemental attributes and time-series sidecars

`infrasys.SupplementalAttribute` subclasses do not require component names. They can be associated with components, own Infrasys time series, and round-trip with their time-series sidecar directory.

Time-series sample magnitudes, timestamps, resolution, and unit names are preserved. Loaded Pint unit objects may be associated with a different registry object than project `BaseQuantity` units, so tests and callers should compare unit strings or dimensionality rather than relying on Pint unit object identity across the sidecar boundary.

### Project quantities

Project quantity classes derive from `infrasys.BaseQuantity`, so they use the Infrasys Pint registry instead of creating an independent registry. Top-level quantity fields on registered components and supplemental attributes serialize with Infrasys metadata.

Nested quantities inside local Pydantic value models require project-side support. `LineDataModel` serializes embedded quantities with Infrasys quantity metadata and restores them before Pydantic validation so values and units survive JSON round trips.

### Schema/version hooks

`TransmissionLineSystem` records both Infrasys `data_format_version` and package-level `transmissionlines_schema_version` metadata. The foundation includes an upgrade hook for metadata-only legacy upgrades and raises for unsupported schema versions.

## Limitation: nested component references inside value models

Infrasys 1.2.1 resolves component references when those references are direct fields on registered `Component` subclasses. It does not preserve registered object identity for component references hidden inside arbitrary nested Pydantic value models.

For example, this shape serializes the nested owner as embedded data instead of an Infrasys component reference:

```python
class NestedReferenceValue(LineDataModel):
    owner: Bus


class Line(Component):
    nested: NestedReferenceValue
```

After a JSON round trip, the nested bus may have the same UUID as the system-owned bus, but it is a separate Python object rather than the object registered in the system. Identity-sensitive code must not rely on this nested value-model shape for component references.

## Smallest compatible modeling approach

Keep the v3 model families from the migration plan:

- use `infrasys.Component` for identity-bearing, registered, named system entities;
- use `LineDataModel(BaseModel)` for immutable embedded values that have no system identity;
- use `OperationAttribute(SupplementalAttribute)` for operational metadata and time-series ownership.

Do not register every value object as a component. Doing so would force names, UUID lifecycle, and system registry semantics onto data that should remain embedded by value.

Instead, place identity-bearing component references directly on registered components, or add an explicit resolver later if a nested value-model shape is unavoidable. For example, prefer:

```python
class LineTechnicalInfo(LineDataModel):
    line_name: str
    nominal_voltage: VoltageKV
    nominal_frequency: Frequency
    earth_resistivity: EarthResistivity


class TransmissionLine(Component):
    from_bus: Bus
    to_bus: Bus
    tower_configuration: TowerConfiguration
    technical_info: LineTechnicalInfo
```

rather than embedding `from_bus` and `to_bus` inside `LineTechnicalInfo`. The same caution applies to future routing shapes that reference `Tower` and `LineSpan` components.

This approach preserves Infrasys identity/reference round trips while keeping immutable engineering data small, frozen, and serialized by value.
