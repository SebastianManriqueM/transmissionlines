Build a line
============

Construction order
------------------

1. Open the catalog with ``build.open_catalog()`` and browse towers, phase
   conductors, and ground wires before fixing exact record IDs.
2. Select equipment with ``build.conductor()`` and ``build.ground_wire()``;
   configure bundles with ``build.bundle()``.
3. Assemble each catalog circuit and its insulator with ``build.tower()``.
4. Create a cross-section with ``build.cross_section_line()`` and run
   ``build.calculations()`` for impedances, St. Clair, and optionally sag.
5. Use ``plots.st_clair()`` or ``plots.sag()`` on stored results.

The :doc:`../quickstart` walks through this workflow, and the complete
:doc:`../how-to/build-cross-section-line` script runs from the checkout.
For uncataloged equipment or routed lines with real terminal buses and
ordered spans, use the lower-level model and builder APIs.
The functions :func:`transmissionlines.api.build_transmission_line` and
:func:`transmissionlines.api.assemble_line_into_system` are helpers for
resolving and registering buses, configuration,
route components, and line into a ``TransmissionLineSystem``. System assembly
validates the candidate before registering new components.

For routed lines with a shared configuration, the calculation selects that
cross-section automatically. Where supports have different configurations,
pass a line-owned ``tower`` explicitly. The returned impedance and St. Clair
curve represent only the selected cross-section, not the whole route.

The result from ``build.calculations`` holds impedance, St. Clair, and sag
outputs outside Infrasys. It does not mutate or persist the input line or
system.