Calculations
============

Line-level orchestration is exposed by :mod:`transmissionlines.api`. The
calculation modules below also provide lower-level matrix, geometry, cable,
and positive-sequence operations.

Electrical orchestration
------------------------

.. automodule:: transmissionlines.calculations.electrical
   :members: build_primitive_z, build_primitive_p, calculate_electrical

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
   :members: calculate_st_clair, calculate_st_clair_curve_for_line, nominal_pi_to_equivalent_pi