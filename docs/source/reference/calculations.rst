Calculations
============

Line-level orchestration lives in :mod:`transmissionlines.calculations.electrical`. The
calculation modules below also provide lower-level matrix, geometry, cable,
and positive-sequence operations.

Electrical orchestration
------------------------

.. automodule:: transmissionlines.calculations.electrical
   :members: build_primitive_z, build_primitive_p, calculate_electrical, calculate_line_electrical_parameters, calculate_st_clair_curve_for_line

Matrix operations
-----------------

.. automodule:: transmissionlines.calculations.matrices
   :members:

Cable derivations
-----------------

.. automodule:: transmissionlines.calculations.cable
   :members:

Geometry operations
-------------------

.. automodule:: transmissionlines.calculations.geometry
   :members:

St. Clair calculations
----------------------

.. automodule:: transmissionlines.calculations.st_clair
   :members: calculate_st_clair, nominal_pi_to_equivalent_pi

Sag calculations
----------------

.. automodule:: transmissionlines.calculations.sag
   :members: calculate_sag, solve_span_sag