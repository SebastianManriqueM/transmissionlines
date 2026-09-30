Plotting
========

St. Clair curves
----------------

``plot_st_clair_curve`` plots an existing ``StClairResult``; it does not rerun
the calculation. It returns a Matplotlib ``Axes``. By default it plots base
curves against line length in miles and receiving-end real power in MW, marks
the active voltage, thermal, or stability limit, and does not show an
interactive window. Pass ``curves="all"`` to include sensitivity curves,
``y="ps_mw"`` for sending-end power, or ``show_voltage_limit=True`` to add
receiving-end voltage and its configured threshold on a second axis.

For a headless script, select a non-interactive Matplotlib backend before
creating figures, then close the figure after saving it:

.. code-block:: python

   import matplotlib
   matplotlib.use("Agg")
   import matplotlib.pyplot as plt

   axes = plot_st_clair_curve(result, show=False)
   axes.figure.savefig("st-clair.png", dpi=150)
   plt.close(axes.figure)

Sag curves
----------

``plot_sag_curve`` plots maximum vertical sag below the attachment chord
against hypothetical horizontal span in feet for an existing ``SagCurveResult``.
It does not rerun the solver or access the line graph. By default it plots all
circuits; pass ``circuit_id`` to select one. It returns a Matplotlib ``Axes``
and does not open an interactive window unless ``show=True``. The stored
horizontal tensions are not plotted by this function.

Given ``line`` and ``options`` as described in the :doc:`sag` guide, save a
headless sag plot with:

.. code-block:: python

   import matplotlib
   matplotlib.use("Agg")
   import matplotlib.pyplot as plt

   from transmissionlines.api import calculate_sag, plot_sag_curve

   sag_result = calculate_sag(line, options=options)
   axes = plot_sag_curve(sag_result, show=False)
   axes.figure.savefig("sag-curve.png", dpi=150)
   plt.close(axes.figure)

Matplotlib is currently declared as a project runtime dependency in
``pyproject.toml``. St. Clair plotting imports ``matplotlib.pyplot`` lazily and
reports a targeted ``ImportError`` if it is unavailable; sag plotting imports
Matplotlib directly. Neither plotting path is an installable optional extra today.