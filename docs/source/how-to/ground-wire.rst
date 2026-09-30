Specify/Select Ground Wire
==========================

The :doc:`../catalog/ground-wire` table describes the available Alumoweld
and ACSR rows. Unlike phase conductors, ground wires have no codeword in this
catalog: select by exact ``record_id``, family plus ``awg_or_stranding`` when
unique, or filter the table by size or diameter and inspect all matches.

.. code-block:: python

   from transmissionlines.api import open_catalog
   from transmissionlines.builders.line import ground_wire_from_record
   from transmissionlines.catalog.schemas import GroundWireRecord

    catalog = open_catalog()
   row = catalog.select_exact("ground_wires", record_id="Alumoweld:7/7:145.7:15")
   same_row = catalog.select_exact(
       "ground_wires", family="Alumoweld", awg_or_stranding="7/7"
   )
   assert row["record_id"] == same_row["record_id"]
   ground_wire = ground_wire_from_record(
       GroundWireRecord.model_validate(row), catalog_version=catalog.catalog_version
   )
   wires = catalog.table("ground_wires")
   matches = wires.loc[
       (wires.family == "Alumoweld") & wires.diameter_inch.between(0.42, 0.45)
   ]
   print(matches[["record_id", "awg_or_stranding", "breaking_load_lb"]]
         .to_string(index=False))

To specify a new ground wire, supply the properties needed by the electrical
calculation. ``BareConductorEquipment`` also accepts optional unit-typed
weight and rated breaking strength when published measurements are available:

.. code-block:: python

   from transmissionlines.models.cables import BareConductorEquipment, GroundWireSpec
   from transmissionlines.units import CableDiameter, ResistancePerKft

   ground_wire = GroundWireSpec(
       name="my-ground-wire",
       equipment=BareConductorEquipment(
           conductor_diameter=CableDiameter(0.43, "inch"),
           dc_resistance=ResistancePerKft(0.35, "ohm / kilofoot"),
       ),
   )

Values are illustrative. ``TowerGeometry.ground_wire_positions`` assigns
each wire a unique position and ID; one ``GroundWireSpec`` is used for all
ground-wire positions in a ``TowerConfiguration``.