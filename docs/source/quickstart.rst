Quick start
===========

Build a line in memory
----------------------

This example constructs one three-phase circuit, one ground wire, its terminal
buses, and technical data without reading a catalog or manufacturer workbook.
The values are illustrative. ``TowerCoordinate`` is in feet, cable properties
carry explicit units, and the example uses a single subconductor per phase.

The example executes as part of the Sphinx doctest build.

.. doctest::

   >>> from transmissionlines.api import calculate_line_electrical_parameters
   >>> from transmissionlines.models.assets import LineTechnicalInfo, TransmissionLine
   >>> from transmissionlines.models.cables import BareConductorEquipment, GroundWireSpec, PhaseConductorSpec
   >>> from transmissionlines.models.common import Bus, GeographicPoint, IdentificationInfo
   >>> from transmissionlines.models.configurations import TowerConfiguration
   >>> from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
   >>> from transmissionlines.models.st_clair import StClairOptions
   >>> from transmissionlines.units import (
   ...     Angle, CableDiameter, CableGMR, Current, EarthResistivity, Frequency,
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
   ...     ground_wire_spec=GroundWireSpec(conductor=conductor),
   ...     phase_conductor_specs=[
   ...         PhaseConductorSpec(conductor=conductor, circuit_id="c1")
   ...     ],
   ... )
   >>> origin = GeographicPoint(latitude=Angle(0, "degree"), longitude=Angle(0, "degree"))
   >>> destination = GeographicPoint(latitude=Angle(1, "degree"), longitude=Angle(1, "degree"))
   >>> technical_info = LineTechnicalInfo(
   ...     line_name="example-line",
   ...     nominal_voltage=VoltageKV(230, "kilovolt"),
   ...     nominal_frequency=Frequency(60, "hertz"),
   ...     earth_resistivity=EarthResistivity(100, "ohm * meter"),
   ...     from_bus=Bus(name="from", location=origin),
   ...     to_bus=Bus(name="to", location=destination),
   ... )
   >>> line = TransmissionLine(
   ...     name="example-line",
   ...     technical_info=technical_info,
   ...     tower_configuration=configuration,
   ... )
   >>> calculated = calculate_line_electrical_parameters(
   ...     line,
   ...     st_clair_options=StClairOptions(
   ...         line_length_start_mi=20.0,
   ...         line_length_stop_mi=20.0,
   ...     ),
   ... )
   >>> electrical = calculated.line_parameters.electrical_parameters
   >>> electrical.status
   'complete'
   >>> electrical.matrices["Zabcg"].row_count
   4
   >>> electrical.matrices["Z012_ft"].row_labels
   ['1:zero', '1:positive', '1:negative']
   >>> electrical.st_clair_curve.curves[0].lengths_mi
   [20.0]
   >>> line.line_parameters is None
   True

The primitive ``Zabcg`` matrix contains three phase conductors plus the ground
wire. ``Z012_ft`` contains the fully transposed symmetrical-component result.
The default St. Clair calculation is attached to the returned copy; the input
line remains unchanged. The short 20-mile sweep above keeps the example quick;
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

Catalog generation needs caller-supplied raw files and explicit source-header
mappings. Open an already generated catalog with :func:`transmissionlines.api.open_catalog`,
select exact normalized records, and pass those records through the builder
workflow. This checkout does not include the original workbook or manufacturer
source files; the in-memory examples above are runnable without them. See
:doc:`concepts/catalog` for catalog versioning and provenance.