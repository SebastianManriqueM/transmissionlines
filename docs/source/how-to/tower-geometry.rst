Specify/Select a Tower Geometry
===============================

Browse the :doc:`../catalog/tower-geometry` table before choosing a structure.
``TowerGeometry`` contains phase and ground-wire **positions**, not just the
summary counts in ``tower_geometries``. An exact structure code is the most
reproducible selector:

.. code-block:: python

   from transmissionlines.api import open_catalog
   from transmissionlines.builders.line import geometry_from_records
   from transmissionlines.catalog.schemas import PhasePositionRecord, GroundWirePositionRecord

    catalog = open_catalog()
   tower = catalog.select_exact(
       "tower_geometries", structure_code="3L11", structure_type="Lattice"
   )
   phases = catalog.table("phase_positions")
   grounds = catalog.table("ground_wire_positions")
   geometry = geometry_from_records(
       [PhasePositionRecord.model_validate(row) for row in
        phases.loc[phases.geometry_id == tower["record_id"]].to_dict("records")],
       [GroundWirePositionRecord.model_validate(row) for row in
        grounds.loc[grounds.geometry_id == tower["record_id"]].to_dict("records")],
   )

To discover by voltage, type, circuits, and ground-wire count, filter the
DataFrame first, inspect all candidates, then select a unique ``record_id``:

.. code-block:: python

   towers = catalog.table("tower_geometries")
   matches = towers.loc[
       (towers.voltage_kv == 345)
       & (towers.structure_type == "Lattice")
       & (towers.n_circuits == 2)
       & (towers.n_ground_w == 2)
   ]
   print(matches[["record_id", "state"]].to_string(index=False))
   tower = catalog.select_exact("tower_geometries", record_id="3L11")

``state`` is unverified free text, sometimes a multi-state list or placeholder;
do not use it as a precise geographic filter. A subset of position records may
have a ``state_id``: pass the exact state ID to ``geometry_from_records`` only
after checking that it retains all three phases for every circuit and at least
one ground wire. Geometry construction validates those requirements.

For a new structure, create a ``TowerGeometry`` directly, with feet-based
coordinates relative to the tower centerline and ground level:

.. code-block:: python

   from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
   from transmissionlines.units import TowerCoordinate

   geometry = TowerGeometry(
       phase_positions=[
           PhasePosition(circuit_id="c1", phase=phase,
                         x=TowerCoordinate(x, "foot"),
                         y=TowerCoordinate(30, "foot"))
           for phase, x in (("A", -8), ("B", 0), ("C", 8))
       ],
       ground_wire_positions=[GroundWirePosition(
           wire_id="g1", x=TowerCoordinate(0, "foot"),
           y=TowerCoordinate(40, "foot"),
       )],
   )

New runtime geometries do not need a catalog row; leave the configuration's
``IdentificationInfo.geometry_id`` unset unless you have a real source ID.