Build a line
============

Construction order
------------------

1. Create ``BareConductorEquipment`` values with the properties needed by the
   chosen calculation.
2. Create ``PhaseConductorSpec`` values, one per circuit, including bundle
   counts and spacing where applicable.
3. Create the required ``GroundWireSpec`` and a ``TowerGeometry`` with complete
   phase sets and at least one ground wire.
4. Combine those values in a reusable ``TowerConfiguration``.
5. Create distinct terminal ``Bus`` values and ``LineTechnicalInfo`` with
   nominal electrical quantities.
6. Construct ``TransmissionLine`` and call
   :func:`transmissionlines.api.calculate_line_electrical_parameters`.

The :doc:`../quickstart` is a complete executable version of this workflow.
The functions :func:`transmissionlines.api.build_transmission_line` and
:func:`transmissionlines.api.assemble_line_into_system` are helpers for
substituting a configuration or resolving/ registering buses, configuration,
route components, and line into a ``TransmissionLineSystem``. System assembly
validates the candidate before registering new components.

Routing is optional and is not consulted for cross-section electrical
parameters. When included, route towers and spans must be consecutive and the
route endpoints must agree with the terminal bus locations.

Calculated results are attached to a copy of the line. The input line and
existing mechanical result are preserved; use the returned line for subsequent
work.