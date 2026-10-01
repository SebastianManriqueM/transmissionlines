Specify a Tower Configuration
=============================

``TowerConfiguration`` joins a :doc:`tower-geometry`, one
:doc:`ground-wire` spec, and exactly one ``CircuitConfiguration`` per circuit
ID in the geometry. The catalog has no pre-built tower configurations and does
not prescribe which cable or insulator is installed on a structure.

For catalog-backed selections, browse candidate records and fix their exact
IDs before assembling circuits. The :doc:`build-cross-section-line` script
also demonstrates this workflow end to end:

.. code-block:: python

   from transmissionlines.user_api import build

   catalog = build.open_catalog()
   geometry_id = catalog.towers(structure_code="3L11")[0]["record_id"]
   conductor = build.conductor(catalog, record_id="ACSR:954:cardinal:standard:54/7")
   ground_wire = build.ground_wire(catalog, record_id="Alumoweld:7/7:145.7:15")
   bundle = build.bundle(subconductor_count=1)
   insulator = {
       "insulator_type": "glass", "number_of_insulators": 12,
       "insulator_code": "U120B", "insulator_coupling": "ball_and_socket",
   }
   circuits = [
       {"circuit_id": circuit_id, "conductor": conductor,
        "bundle": bundle, "insulator": insulator}
       for circuit_id in catalog.tower_circuits(geometry_id)
   ]
   tower = build.tower(
       catalog, name="selected-tower", geometry_id=geometry_id,
       ground_wire=ground_wire, circuits=circuits,
   )

For bundled phases use ``build.bundle(subconductor_count=2,
subconductor_spacing_in=18)`` (with an appropriate physical spacing). Supply
the insulator independently because it is not in the catalog. For new
structures or equipment not in the catalog, use the lower-level
:doc:`../reference/builders` and do not claim a catalog geometry ID.