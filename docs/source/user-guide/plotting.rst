Plotting
========

St. Clair curves
----------------

``plots.st_clair`` plots an existing ``StClairResult``; it does not rerun the
calculation. It returns a Matplotlib ``Axes`` with base curves against line
length in miles and receiving-end real power in MW. It marks the active
voltage, thermal, or stability limit without opening an interactive window.
For sensitivity curves or alternate axes, see the advanced
:func:`transmissionlines.api.plot_st_clair_curve` interface.

For a headless script, select a non-interactive Matplotlib backend before
creating figures, then close the figure after saving it:

.. code-block:: python

   import matplotlib
   matplotlib.use("Agg")
   import matplotlib.pyplot as plt
   from sys import path
   path.insert(0, "docs/source/how-to/examples")
   from catalog_line import build_line
   from transmissionlines.user_api import build, plots

   line = build_line()
   results = build.calculations(line, sag=False)
   axes = plots.st_clair(results.st_clair)
   axes.figure.savefig("st-clair.png", dpi=150)
   plt.close(axes.figure)

Sag curves
----------

``plots.sag`` plots maximum vertical sag below the attachment chord
against hypothetical horizontal span in feet for an existing ``SagCurveResult``.
It does not rerun the solver or access the line graph. By default it plots all
circuits; pass ``circuit_id`` to select one. It returns a Matplotlib ``Axes``
and does not open an interactive window. The stored
horizontal tensions are not plotted by this function.

Given a catalog-backed line, save a headless sag plot with:

.. code-block:: python

   import matplotlib
   matplotlib.use("Agg")
   import matplotlib.pyplot as plt

      from sys import path
      path.insert(0, "docs/source/how-to/examples")
      from catalog_line import build_line
      from transmissionlines.user_api import build, plots

      line = build_line()
      line.everyday_tension_fraction = 0.20
      results = build.calculations(
         line, impedances=False, st_clair=False,
         sag_options={
            "elastic_modulus_psi": 11.5e6, "thermal_expansion_per_k": 19.3e-6,
            "span_start_ft": 20, "span_stop_ft": 2000, "span_step_ft": 10,
         },
      )
      axes = plots.sag(results.sag)
   axes.figure.savefig("sag-curve.png", dpi=150)
   plt.close(axes.figure)

Matplotlib is a project runtime dependency. Neither plotting path is an
installable optional extra today.