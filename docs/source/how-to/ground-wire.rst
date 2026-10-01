Specify/Select Ground Wire
==========================

The :doc:`../catalog/ground-wire` table describes the available Alumoweld
and ACSR rows. Unlike phase conductors, ground wires have no codeword in this
catalog: select by exact ``record_id``, family plus ``awg_or_stranding`` when
unique, or filter the table by size or diameter and inspect all matches.

.. code-block:: python

   from transmissionlines.user_api import build

   catalog = build.open_catalog()
   matches = catalog.ground_wires(family="Alumoweld", diameter_min_in=0.42,
                                  diameter_max_in=0.45)
   print(catalog.format_choices(matches))
   ground_wire = build.ground_wire(catalog, record_id="Alumoweld:7/7:145.7:15")

For wire properties not present in the catalog, see the lower-level
:doc:`../reference/builders`. Electrical calculations require ground-wire
diameter and DC resistance. A tower uses one selected ground-wire spec for
all of its ground-wire positions.