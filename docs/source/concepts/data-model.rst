Transmission-line input model
=============================

The input schema uses Infrasys for registered, static components only. Version
4 does not load older system files. Electrical and St. Clair calculations use
these inputs but return standalone typed results outside the Infrasys system;
the input graph and serialized system contain no calculated matrices or curves.

.. mermaid::
   :name: transmission-line-input-model
   :alt: Cross-section and routed line input references

   classDiagram
     AbstractTransmissionLine <|-- CrossSectionTransmissionLine
     AbstractTransmissionLine <|-- RoutedTransmissionLine
     CrossSectionTransmissionLine --> TowerConfiguration : representative
     RoutedTransmissionLine --> Bus : terminals
     RoutedTransmissionLine --> LineSpan : ordered
     LineSpan --> StartEnd : references
     StartEnd --> ElectricalTower : endpoints
     ElectricalTower --> TowerConfiguration : installed
     TowerConfiguration --> CircuitConfiguration : circuits
     TowerConfiguration --> GroundWireSpec : shared
     CircuitConfiguration --> ConductorSpec : shared
     CircuitConfiguration --> BundleSpec : embeds
     CircuitConfiguration --> InsulatorStringSpec : embeds

``AbstractTransmissionLine`` owns positive nominal voltage, frequency, and
earth resistivity. A ``CrossSectionTransmissionLine`` requires one registered
representative ``TowerConfiguration``; it has no physical tower, bus, or route.
A ``RoutedTransmissionLine`` requires distinct terminal buses and nonempty
ordered spans. Each ``LineSpan`` references a ``StartEnd`` component containing
real, distinct ``ElectricalTower`` endpoints. Each tower selects its own
registered configuration, structure form, and support role. Consecutive spans
share the same tower at their join; the first and last supports are terminals.

``RouteGeometry`` embeds WGS84 coordinates for a single span, supplied directly
without requiring a GeoJSON file. The first and last coordinates must match
the endpoint towers, whose terminal locations must match their buses. A route
does not store a second tower list or a derived span length.

``TowerConfiguration`` references registered ``CircuitConfiguration`` objects
with IDs matching its ``TowerGeometry`` phase positions. A circuit references
a reusable ``ConductorSpec`` and embeds its own ``BundleSpec`` and required
``InsulatorStringSpec``. One registered ``GroundWireSpec`` is shared by the
configuration's ground-wire positions. These cable components hold selected
manufacturer measurements and optional compact catalog provenance, not
calculated GMRs, electrical matrices, ratings, or curves.