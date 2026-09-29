Specify a Tower Configuration
=============================

``TowerConfiguration`` joins a :doc:`tower-geometry`, one
:doc:`ground-wire` spec, and exactly one ``CircuitConfiguration`` per circuit
ID in the geometry. The catalog has no pre-built tower configurations and does
not prescribe which cable or insulator is installed on a structure.

For catalog-backed selections, validate the returned dictionaries using
``ConductorRecord``/``GroundWireRecord`` before passing them to builders. The
:doc:`build-cross-section-line` script does this from the beginning. Once you
have ``geometry``, ``catalog``, a ``conductor_record`` and a
``ground_wire_record``, create the configuration as follows:

.. code-block:: python

   from transmissionlines.builders.line import ground_wire_from_record, phase_spec_from_record
   from transmissionlines.models.cables import InsulatorStringSpec
   from transmissionlines.models.common import IdentificationInfo
   from transmissionlines.models.configurations import TowerConfiguration

   insulator = InsulatorStringSpec(
       insulator_type="glass", number_of_insulators=12,
       insulator_code="U120B", insulator_coupling="ball_and_socket",
   )
   circuits = [
       phase_spec_from_record(
           conductor_record, circuit_id=circuit_id,
           insulator_string=insulator, catalog_version=catalog.catalog_version,
       )
       for circuit_id in sorted({position.circuit_id for position in geometry.phase_positions})
   ]
   configuration = TowerConfiguration(
       name="selected-tower",
       identification_info=IdentificationInfo(geometry_id="3L11", structure_code="3L11"),
       geometry=geometry,
       circuits=circuits,
       ground_wire_spec=ground_wire_from_record(
           ground_wire_record, catalog_version=catalog.catalog_version
       ),
   )

For bundled phases set ``subconductor_count`` and a positive
``subconductor_spacing=BundleSpacing(value, "inch")`` on
``phase_spec_from_record``; the default is one subconductor. Specify the
physical insulator independently because it is not in the catalog.

For components absent from the catalog, assemble the manually specified
``geometry``, ``conductor``, and ``ground_wire`` from the preceding recipes:

.. code-block:: python

   from transmissionlines.models.cables import BundleSpec
   from transmissionlines.models.configurations import CircuitConfiguration

   custom_configuration = TowerConfiguration(
       name="custom-tower",
       identification_info=IdentificationInfo(),
       geometry=geometry,
       ground_wire_spec=ground_wire,
       circuits=[CircuitConfiguration(
           name="custom-c1", circuit_id="c1", conductor_spec=conductor,
           bundle_spec=BundleSpec(subconductor_count=1),
           insulator_string=insulator,
       )],
   )

The ``insulator`` is the ``InsulatorStringSpec`` defined above. Do not claim
a catalog geometry ID for a new structure. See the complete non-catalog
example in :doc:`../quickstart`.