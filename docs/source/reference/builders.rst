Builders
========

The public facade exports ``BusDefinition``, ``build_transmission_line``, and
``assemble_line_into_system``. They construct a line copy or resolve and
register a validated line graph in ``TransmissionLineSystem``. See the
:doc:`../user-guide/build-a-line` guide for construction order and ownership.

.. automodule:: transmissionlines.builders.system
   :members: BusDefinition, build_transmission_line, assemble_line_into_system