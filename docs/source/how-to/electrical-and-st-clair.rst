Obtain Electrical Parameters and St. Clair Curve
================================================

The :doc:`build-cross-section-line` script selects exact catalog records and
calls ``build.calculations``. The result does not modify the input line:

.. code-block:: console

   uv run python docs/source/how-to/examples/catalog_line.py

To examine and plot the output in your own script, import ``build_line`` from
that example (or use the same construction steps), then run:

.. code-block:: python

   from sys import path

   path.insert(0, "docs/source/how-to/examples")
   from catalog_line import build_line
   from transmissionlines.user_api import build, plots

   line = build_line()
   result = build.calculations(
       line, st_clair_options={"line_length_start_mi": 20,
                               "line_length_stop_mi": 600}, sag=False,
   )
   impedances = result.impedances
   print(impedances.status)
   for circuit in result.st_clair.curves:
       print(circuit.circuit_id, circuit.lengths_mi, circuit.pr_mw)
    axes = plots.st_clair(result.st_clair)
   axes.figure.savefig("st-clair.png", dpi=150)

The default line-length sweep is 20--600 miles. The script on the preceding
page uses only 20 miles for a fast example. This calculation needs phase AC
resistance, geometry, ground-wire diameter and DC resistance, and conductor
ampacity. The v2 Cardinal record lacks published GMR; ``build.conductor``
warns when it estimates GMR from outer radius. Check catalog and manufacturer
data before relying on calculated results.

``impedances.matrices`` includes the primitive ``Zabcg`` and fully transposed
sequence ``Z012_ft`` matrices. The St. Clair result contains one loadability
curve per circuit, including length, receiving-end MW, limiting criterion,
and voltage/current arrays. For another line-length sweep, call
``build.calculations`` again with different ``st_clair_options``; for plotting
details see :doc:`../user-guide/plotting`. For assumptions and
units see :doc:`../user-guide/electrical-models` and
:doc:`../user-guide/st-clair`. These cross-section results do not represent
a full routed line with heterogeneous structures.