Specify/Select a Conductor
==========================

See the :doc:`../catalog/phase-conductors` family table for sizes and units.
Codewords repeat across families and sometimes within one family. Use the
exact ``record_id`` or a combination that selects **one** row:

.. code-block:: python

   from transmissionlines.api import open_catalog
   from transmissionlines.builders.line import conductor_from_record
   from transmissionlines.catalog.schemas import ConductorRecord

   catalog = open_catalog("data/catalog/v1")
   row = catalog.select_exact("conductors", record_id="ACSR:Cardinal:954.0:21")
   same_row = catalog.select_exact(
       "conductors", family="ACSR", codeword="Cardinal", stranding="54/7"
   )
   assert row["record_id"] == same_row["record_id"]
   record = ConductorRecord.model_validate(row)
   conductor = conductor_from_record(record, catalog_version=catalog.catalog_version)

For a diameter or size criterion, discover candidates in the DataFrame and
check family, codeword, stranding, ampacity, and resistance before committing
to one ``record_id``. Values are inches and kcmil; this is a **range search**,
not an automatic substitute for electrical or mechanical equivalence:

.. code-block:: python

   cables = catalog.table("conductors")
   matches = cables.loc[
       (cables.family == "ACSR") & cables.diameter_inch.between(1.19, 1.20)
   ]
   print(matches[["record_id", "codeword", "stranding", "size_kcmil",
                  "ampacity_a"]].to_string(index=False))
   row = catalog.select_exact("conductors", record_id="ACSR:Cardinal:954.0:21")

For a cable not in the catalog, provide measured properties and a distinct
name directly. No ``CatalogReference`` is attached to this component:

.. code-block:: python

   from transmissionlines.models.cables import BareConductorEquipment, ConductorSpec
   from transmissionlines.units import CableDiameter, CableGMR, Current, ResistancePerKft

   conductor = ConductorSpec(
       name="my-phase-conductor",
       equipment=BareConductorEquipment(
           conductor_diameter=CableDiameter(1.1, "inch"),
           conductor_gmr=CableGMR(0.04, "foot"),
           ampacity=Current(900, "ampere"),
           ac_resistance=ResistancePerKft(0.025, "ohm / kilofoot"),
           dc_resistance=ResistancePerKft(0.02, "ohm / kilofoot"),
       ),
   )

These values are illustrative; use manufacturer data for actual equipment.
Electrical calculations require an AC resistance and sufficient diameter/GMR
or capacitance-radius data to derive bundle properties; line-level St. Clair
also requires ampacity. For catalog records, ``phase_spec_from_record`` adds
the circuit ID, bundle, and insulator string (see :doc:`tower-configuration`).