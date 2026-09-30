Specify/Select a Conductor
==========================

See the :doc:`../catalog/phase-conductors` family table for sizes and units.
Codewords repeat across families and sometimes within one family. Use the
exact ``record_id`` or a combination that selects **one** row:

.. code-block:: python

   from transmissionlines.api import open_catalog
   from transmissionlines.builders.line import conductor_from_record
    from transmissionlines.catalog.schemas import ConductorV2Record

    catalog = open_catalog()
    row = catalog.select_exact("conductors", family="ACCC", codeword="IRVING", variant="uls")
    record = ConductorV2Record.model_validate(row)
   conductor = conductor_from_record(record, catalog_version=catalog.catalog_version)
    assert conductor.equipment.weight is not None
    assert conductor.equipment.rated_breaking_strength is not None
    assert conductor.equipment.total_material_area is not None

``variant="standard"`` selects the other ACCC IRVING construction. Omitting
``variant`` raises ``AmbiguousCatalogMatch`` rather than choosing one. An exact
``record_id`` also works; keep ``catalog_version="v2"`` on references to v2
records. Nullable Parquet cells become ``None`` when selected through the
repository. The model carries weight in lbf/kft, strength in lbf, and total
material area in in2. Missing measurements remain ``None``; sag must reject
them when required.

For a diameter or size criterion, discover candidates in the DataFrame and
check family, codeword, variant, published ampacity conditions, and resistance
before committing to one ``record_id``. Diameter is in inches; ``size`` is a
source label and ``size_kcmil`` is nullable. This is a **range search**,
not an automatic substitute for electrical or mechanical equivalence:

.. code-block:: python

   cables = catalog.table("conductors")
   matches = cables.loc[
       (cables.family == "ACSR") & cables.diameter_inch.between(1.19, 1.20)
   ]
   print(matches[["record_id", "codeword", "variant", "size",
                  "ampacity_75c_a"]].to_string(index=False))
   row = catalog.select_exact("conductors", record_id=matches.iloc[0].record_id)

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