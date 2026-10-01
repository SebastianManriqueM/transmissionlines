Specify/Select a Tower Geometry
===============================

Browse the :doc:`../catalog/tower-geometry` table before choosing a structure.
``TowerGeometry`` contains phase and ground-wire **positions**, not just the
summary counts in ``tower_geometries``. An exact structure code is the most
reproducible selector:

.. code-block:: python

   from transmissionlines.user_api import build

   catalog = build.open_catalog()
   choices = catalog.towers(structure_code="3L11", structure_type="Lattice")
   print(catalog.format_choices(choices))
   geometry_id = choices[0]["record_id"]
   circuit_ids = catalog.tower_circuits(geometry_id)

To discover by voltage, type, circuits, and ground-wire count, inspect all
candidates before fixing a unique ``record_id``:

.. code-block:: python

   matches = catalog.towers(
       voltage_min_kv=345, voltage_max_kv=345, structure_type="Lattice",
       n_circuits=2, n_ground_wires=2,
   )
   print(catalog.format_choices(matches))

The browser validates all A/B/C phases for each returned circuit ID before
configuring a tower. For a new, uncataloged geometry use the lower-level
:doc:`../reference/builders`; do not assign it a catalog geometry ID.