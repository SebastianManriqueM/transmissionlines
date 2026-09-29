Build a line
============

Construction order
------------------

1. Create ``BareConductorEquipment`` values with the properties needed by the
   chosen calculation.
2. Create reusable ``ConductorSpec`` components and ``CircuitConfiguration``
   components with their bundle and required insulator inputs.
3. Create the required ``GroundWireSpec`` and a ``TowerGeometry`` with complete
   phase sets and at least one ground wire.
4. Combine those values in a reusable ``TowerConfiguration``.
5. Construct ``CrossSectionTransmissionLine`` with the representative
   configuration and nominal electrical quantities, or a ``RoutedTransmissionLine``
   with real terminal buses, configured supports and ordered spans.
6. Call
   :func:`transmissionlines.api.calculate_line_electrical_parameters`.

The :doc:`../quickstart` is a complete in-memory version of this workflow.
For a catalog-backed, end-to-end script, see
:doc:`../how-to/build-cross-section-line`.
The functions :func:`transmissionlines.api.build_transmission_line` and
:func:`transmissionlines.api.assemble_line_into_system` are helpers for
resolving and registering buses, configuration,
route components, and line into a ``TransmissionLineSystem``. System assembly
validates the candidate before registering new components.

For routed lines with a shared configuration, the calculation selects that
cross-section automatically. Where supports have different configurations,
pass a line-owned ``tower`` explicitly. The returned impedance and St. Clair
curve represent only the selected cross-section, not the whole route.

The returned ``LineCalculationResult`` holds electrical and St. Clair outputs
outside Infrasys. It does not mutate or persist the input line or system.