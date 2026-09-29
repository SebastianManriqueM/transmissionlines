Obtain Electrical Parameters and St. Clair Curve
================================================

The :doc:`build-cross-section-line` script starts with catalog row selection,
constructs every component and invokes
:func:`transmissionlines.api.calculate_line_electrical_parameters`. Run the
complete script first; its calculation returns an external
``LineCalculationResult`` and does not modify the input line:

.. code-block:: console

   uv run python docs/source/how-to/examples/catalog_line.py

To examine and plot the output in your own script, import ``build_line`` from
that example (or use the same construction steps), then run:

.. code-block:: python

   from sys import path

   path.insert(0, "docs/source/how-to/examples")
   from catalog_line import build_line
   from transmissionlines.api import (
       calculate_line_electrical_parameters,
       plot_st_clair_curve,
   )
   from transmissionlines.models.st_clair import StClairOptions

   line = build_line()
   result = calculate_line_electrical_parameters(
       line,
       st_clair_options=StClairOptions(
           line_length_start_mi=20, line_length_stop_mi=600,
       ),
   )
   electrical = result.electrical
   print(electrical.status)
   for circuit in result.st_clair.curves:
       print(circuit.circuit_id, circuit.lengths_mi, circuit.pr_mw)
   axes = plot_st_clair_curve(result.st_clair, show=False)
   axes.figure.savefig("st-clair.png", dpi=150)

The default line-length sweep is 20--600 miles. The script on the preceding
page uses only 20 miles for a fast example. This calculation requires phase
AC resistance, geometry and diameter/GMR or equivalent capacitance-radius
data, ground-wire diameter and DC resistance, and conductor ampacity. Records
missing these inputs cannot be used as-is for this combined call. Inspect
catalog values and manufacturer data before relying on calculated results.

``electrical.matrices`` includes the primitive ``Zabcg`` and fully transposed
sequence ``Z012_ft`` matrices. The St. Clair result contains one loadability
curve per circuit, including length, receiving-end MW, limiting criterion,
and voltage/current arrays. For separate recalculation with other operating
options, call ``calculate_st_clair_curve(line, previous=result, options=...)``;
for plotting details see :doc:`../user-guide/plotting`. For assumptions and
units see :doc:`../user-guide/electrical-models` and
:doc:`../user-guide/st-clair`. These cross-section results do not represent
a full routed line with heterogeneous structures.