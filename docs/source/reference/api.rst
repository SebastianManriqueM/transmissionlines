Public API
==========

The everyday import surface is :mod:`transmissionlines.user_api`: ``build`` for
catalog browsing, selection, line construction, and calculations, and ``plots``
for stored results. Lower-level functions, such as routed lines, direct
St. Clair constants, and system assembly, are imported from the modules that
define them; see the other reference pages. The top-level ``transmissionlines``
package exports the system and value-model base classes.

.. automodule:: transmissionlines.user_api.build
   :members:

.. automodule:: transmissionlines.user_api.plots
   :members:
