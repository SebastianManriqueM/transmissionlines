Quick start
===========

Build a catalog-backed line
---------------------------

The bundled v2 catalog provides a two-circuit 3L11 structure, Cardinal phase
conductor, and Alumoweld ground wire. Select exact records after browsing the
available choices; the insulator, frequency, and earth resistivity below are
illustrative design inputs. No workbook or manual unit conversions are needed.

The example executes as part of the Sphinx doctest build.

.. doctest::

   >>> from transmissionlines.user_api import build, plots
   >>> catalog = build.open_catalog()
   >>> tower_row = catalog.towers(structure_code="3L11")[0]
   >>> conductor = build.conductor(catalog, record_id="ACSR:954:cardinal:standard:54/7")
   >>> ground_wire = build.ground_wire(catalog, record_id="Alumoweld:7/7:145.7:15")
   >>> circuit_ids = catalog.tower_circuits(tower_row["record_id"])
   >>> tower = build.tower(
   ...     catalog, name="3L11-cardinal", geometry_id=tower_row["record_id"],
   ...     ground_wire=ground_wire,
   ...     circuits=[{
   ...         "circuit_id": circuit_id, "conductor": conductor,
   ...         "bundle": build.bundle(subconductor_count=1),
   ...         "insulator": {
   ...             "insulator_type": "glass", "number_of_insulators": 12,
   ...             "insulator_code": "U120B", "insulator_coupling": "ball_and_socket",
   ...         },
   ...     } for circuit_id in circuit_ids],
   ... )
   >>> line = build.cross_section_line(
   ...     tower, name="3L11-example", voltage_kv=tower_row["voltage_kv"], frequency_hz=60,
   ...     earth_resistivity_ohm_m=100,
   ... )
   >>> results = build.calculations(
   ...     line, st_clair_options={"line_length_stop_mi": 20}, sag=False,
   ... )
   >>> results.impedances.status
   'complete'
   >>> len(results.st_clair.curves)
   2
   >>> results.st_clair.curves[0].lengths_mi
   [20.0]
   >>> "line_parameters" not in type(line).model_fields
   True
   >>> axes = plots.st_clair(results.st_clair)
   >>> axes.get_xlabel()
   'Line length (mi)'

The calculation results are separate from the input line. ``Z012_ft`` in
``results.impedances.matrices`` is the transposed sequence matrix; St. Clair
returns one curve per circuit. The 20-mile sweep is intentionally short; the
default sweep extends to 600 miles. Catalog v2 Cardinal lacks a published GMR,
so impedance calculations warn when they estimate it from the outer radius.

The plotting function returns a Matplotlib axes and does not call ``show()`` by
default, so it can be used by scripts and headless workflows. The numerical
result is calculated once and then plotted from its stored arrays.

The checkout includes a v2 Parquet snapshot and a historical v1 workbook.
See :doc:`how-to/build-cross-section-line` for the complete runnable script,
and :doc:`concepts/catalog` for versioning and provenance. For standalone
positive-sequence inputs without a tower model, use the advanced
:func:`transmissionlines.api.calculate_st_clair_curve` interface.