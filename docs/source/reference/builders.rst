Builders
========

``build_transmission_line`` returns a validated concrete input line.
``assemble_line_into_system`` registers its graph and resolves reusable
type/name references before mutating the system. A cross-section line registers
no bus, tower, or span; a routed line registers its physical endpoints.
The existing :doc:`../user-guide/build-a-line` calculation example still uses
the old line shape and awaits calculation-result refactoring.

.. automodule:: transmissionlines.builders.system
   :members: build_transmission_line, assemble_line_into_system