Plotting
========

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

Matplotlib is currently declared as a project runtime dependency in
``pyproject.toml``. The plotting module itself imports ``matplotlib.pyplot``
lazily and reports a targeted ``ImportError`` if it is unavailable; this code
behavior does not make it an installable optional extra today.