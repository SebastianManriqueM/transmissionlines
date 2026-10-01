Cross-section user API
======================

Use ``build`` and ``plots`` for explicit catalog selection, reusable tower
configurations, optional registration, and external calculations. Run this
example from the repository root with
``uv run python docs/source/how-to/examples/cross_section_user_api.py``.
The example's voltage, insulator, tension, elastic modulus, and expansion
coefficient are illustrative user inputs, not catalog recommendations.

.. literalinclude:: ../how-to/examples/cross_section_user_api.py
   :language: python

Discovery never selects a row automatically: inspect
``catalog.format_choices(tower_choices)`` and the other choice lists, then
explicitly set IDs. The script pins an eligible conductor with published GMR.
For other rows, the backend derives GMR from catalog internal reactance or
estimates it from verified round ``6/1`` strand dimensions or the outer
radius; estimated values emit a warning and need engineering verification.
Only supply ``gmr_ft`` to ``build.conductor`` when backed by an independent
measured source, and document that source with your study. It takes precedence
over estimates but not published or reactance-derived GMR. The resulting
catalog reference still identifies only the catalog row. See
:doc:`electrical-models` for the equations and limitations.

``build.calculations(line)`` requests every computable group. Missing sag
material options leave sag absent and explain the required inputs in
``results.skipped``. Use ``impedances=False``, ``st_clair=False``, or
``sag=False`` to disable a group; disabling impedances still allows St. Clair
to use electrical inputs internally. St. Clair lengths are hypothetical line
lengths, while sag spans are hypothetical horizontal spans. Neither creates
placed supports or registers calculation results in the input system.