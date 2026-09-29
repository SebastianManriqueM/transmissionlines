Builders
========

``build_transmission_line`` returns a validated concrete input line.
``assemble_line_into_system`` registers its graph and resolves reusable
type/name references before mutating the system. A cross-section line registers
no bus, tower, or span; a routed line registers its physical endpoints.
See :doc:`../user-guide/build-a-line` for calculating standalone results
from either concrete line type.

.. automodule:: transmissionlines.builders.system
   :members: build_transmission_line, assemble_line_into_system