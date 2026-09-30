Quick start
===========

Build a line in memory
----------------------

This example constructs one three-phase cross-section and one ground wire
without reading a catalog or manufacturer workbook.
The values are illustrative. ``TowerCoordinate`` is in feet, cable properties
carry explicit units, and the example uses a single subconductor per phase.

The example executes as part of the Sphinx doctest build.

.. doctest::

   >>> from transmissionlines.api import calculate_line_electrical_parameters
   >>> from transmissionlines.models.assets import CrossSectionTransmissionLine
   >>> from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec, GroundWireSpec, InsulatorStringSpec
   >>> from transmissionlines.models.common import IdentificationInfo
   >>> from transmissionlines.models.configurations import CircuitConfiguration, TowerConfiguration
   >>> from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
   >>> from transmissionlines.models.st_clair import StClairOptions
   >>> from transmissionlines.units import (
   ...     CableDiameter, CableGMR, Current, EarthResistivity, Frequency,
   ...     ResistancePerKft, TowerCoordinate, VoltageKV,
   ... )
   >>> conductor = BareConductorEquipment(
   ...     conductor_diameter=CableDiameter(1, "inch"),
   ...     conductor_gmr=CableGMR(0.04, "foot"),
   ...     ampacity=Current(1000, "ampere"),
   ...     ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot"),
   ...     dc_resistance=ResistancePerKft(0.2, "ohm / kilofoot"),
   ... )
   >>> geometry = TowerGeometry(
   ...     phase_positions=[
   ...         PhasePosition(circuit_id="c1", phase=phase,
   ...                       x=TowerCoordinate(x, "foot"),
   ...                       y=TowerCoordinate(30, "foot"))
   ...         for phase, x in (("A", 0), ("B", 4), ("C", 8))
   ...     ],
   ...     ground_wire_positions=[
   ...         GroundWirePosition(wire_id="g1", x=TowerCoordinate(0, "foot"),
   ...                            y=TowerCoordinate(40, "foot"))
   ...     ],
   ... )
   >>> configuration = TowerConfiguration(
   ...     name="example-configuration",
   ...     identification_info=IdentificationInfo(),
   ...     geometry=geometry,
   ...     ground_wire_spec=GroundWireSpec(name="ground", equipment=conductor),
   ...     circuits=[
   ...         CircuitConfiguration(
   ...             name="c1", circuit_id="c1",
   ...             conductor_spec=ConductorSpec(name="phase", equipment=conductor),
   ...             bundle_spec=BundleSpec(subconductor_count=1),
   ...             insulator_string=InsulatorStringSpec(
   ...                 insulator_type="glass", number_of_insulators=12,
   ...                 insulator_code="U120B", insulator_coupling="ball_and_socket",
   ...             ),
   ...         )
   ...     ],
   ... )
   >>> line = CrossSectionTransmissionLine(
   ...     name="example-line", configuration=configuration,
   ...     nominal_voltage=VoltageKV(230, "kilovolt"),
   ...     nominal_frequency=Frequency(60, "hertz"),
   ...     earth_resistivity=EarthResistivity(100, "ohm * meter"),
   ... )
   >>> calculated = calculate_line_electrical_parameters(
   ...     line,
   ...     st_clair_options=StClairOptions(
   ...         line_length_start_mi=20.0,
   ...         line_length_stop_mi=20.0,
   ...     ),
   ... )
   >>> electrical = calculated.electrical
   >>> electrical.status
   'complete'
   >>> electrical.matrices["Zabcg"].row_count
   4
   >>> electrical.matrices["Z012_ft"].row_labels
   ['1:zero', '1:positive', '1:negative']
   >>> calculated.st_clair.curves[0].lengths_mi
   [20.0]
   >>> "line_parameters" not in type(line).model_fields
   True

The primitive ``Zabcg`` matrix contains three phase conductors plus the ground
wire. ``Z012_ft`` contains the fully transposed symmetrical-component result.
The default St. Clair curve is a sibling of the electrical result in a standalone
envelope; the input line remains unchanged. The short 20-mile sweep keeps the example quick;
the default production grid spans 20 through 600 miles.

Calculate and plot a standalone curve
-------------------------------------

An explicit positive-sequence mapping is useful when a complete tower model is
not needed. The inputs below are in natural units; shunt susceptance is supplied
in siemens per mile. Ampacity is required because the thermal boundary is part
of the calculation.

.. doctest::

   >>> from transmissionlines.api import calculate_st_clair_curve, plot_st_clair_curve
   >>> from transmissionlines.models.st_clair import StClairOptions
   >>> standalone = calculate_st_clair_curve(
   ...     positive_sequence={
   ...         "circuit_id": "example",
   ...         "nominal_voltage_kv": 345.0,
   ...         "r_ohm_per_mile": 0.0012,
   ...         "x_ohm_per_mile": 0.012,
   ...         "b_siemens_per_mile": 0.0008,
   ...         "conductor_ampacity_a": 1000.0,
   ...     },
   ...     options=StClairOptions(
   ...         line_length_start_mi=20.0,
   ...         line_length_stop_mi=20.0,
   ...     ),
   ... )
   >>> standalone.curves[0].lengths_mi
   [20.0]
   >>> standalone.curves[0].pr_mw[0] > 0
   True
   >>> axes = plot_st_clair_curve(standalone, show=False)
   >>> axes.get_xlabel()
   'Line length (mi)'

The plotting function returns a Matplotlib axes and does not call ``show()`` by
default, so it can be used by scripts and headless workflows. The numerical
result is calculated once and then plotted from its stored arrays.

Catalog-backed construction
---------------------------

The checkout includes the default ``data/catalog/v2`` Parquet snapshot and
the historical ``data/catalog/v1`` workbook snapshot. Call
:func:`transmissionlines.api.open_catalog` without a path to open v2,
select exact normalized records, validate them with the corresponding catalog
schema models, and pass them to the record-based builders. See the complete
:doc:`how-to/build-cross-section-line` script. Regenerating the catalog from
other raw files requires explicit source-header mappings; the in-memory
examples above do not require catalog files. See :doc:`concepts/catalog` for
versioning and provenance.