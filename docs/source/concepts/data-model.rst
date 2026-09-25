Transmission-line data model
============================

Object graph
------------

The package separates registered Infrasys components from immutable embedded
values and calculated outputs. The diagram shows the common ownership shape;
routing and calculated results are optional.

.. mermaid::
   :name: transmission-line-model
   :alt: Transmission-line component ownership and embedded engineering values
   :caption: Transmission-line data model ownership

   classDiagram
     class TransmissionLine
     class LineTechnicalInfo
     class Bus
     class TowerConfiguration
     class TowerGeometry
     class PhasePosition
     class GroundWirePosition
     class PhaseConductorSpec
     class GroundWireSpec
     class RoutingInfo
     class Tower
     class LineSpan
     class LineParameters
     class ElectricalParameters
     class MechanicalParameters
     class StClairResult
     TransmissionLine *-- LineTechnicalInfo : owns
     LineTechnicalInfo --> Bus : from and to references
     TransmissionLine --> TowerConfiguration : references
     TowerConfiguration *-- TowerGeometry : embeds
     TowerGeometry *-- PhasePosition : contains
     TowerGeometry *-- GroundWirePosition : contains
     TowerConfiguration *-- PhaseConductorSpec : contains per circuit
     TowerConfiguration *-- GroundWireSpec : contains shared spec
     TransmissionLine --> RoutingInfo : optional route
     RoutingInfo --> Tower : ordered references
     RoutingInfo --> LineSpan : ordered references
     TransmissionLine *-- LineParameters : optional results
     LineParameters *-- ElectricalParameters : contains
     LineParameters *-- MechanicalParameters : contains
     ElectricalParameters *-- StClairResult : optional curve

``TransmissionLine``
--------------------

``TransmissionLine`` is the identity-bearing line component. It names the
line, owns its ``LineTechnicalInfo`` value, references a reusable
``TowerConfiguration``, and may carry route and calculated-parameter values.
The line name must match ``technical_info.line_name``. Terminal buses must be
distinct. If routing is supplied, the first and last tower locations must
match the terminal bus locations.

``LineTechnicalInfo``
---------------------

This immutable ``LineDataModel`` contains ``line_name``, nominal voltage,
frequency, earth resistivity, and the from/to ``Bus`` references. The technical
quantities must be positive. Bus references are direct fields on the registered
line so Infrasys can restore registered component identity during system load.

``TowerConfiguration`` and ``TowerGeometry``
---------------------------------------------

``TowerConfiguration`` is a reusable Infrasys component combining source
identification, tower geometry, one ground-wire specification, and exactly one
phase-conductor specification for each circuit represented by the geometry.
``TowerGeometry`` is an immutable value containing tower-local coordinates:

* ``PhasePosition`` identifies a circuit and one of phases A, B, or C.
  Every configured circuit must have exactly one position for each phase.
* ``GroundWirePosition`` identifies an unbundled ground wire. At least one
  ground-wire position is required by the electrical model.
* ``TowerCoordinate`` values express ``x`` and ``y`` in feet.

Duplicate phase positions, duplicate ground-wire IDs, incomplete phase sets,
and empty circuit geometry are rejected during model validation.

Conductor and ground-wire specifications
----------------------------------------

``BareConductorEquipment`` contains manufacturer-provided or user-provided
physical properties: diameter, GMR, optional capacitance radius, ampacity,
AC resistance, emergency ampacity, and DC resistance. Optional values are
represented explicitly and calculation entry points report required values
that are absent.

``PhaseConductorSpec`` associates one conductor with a circuit and defines the
subconductor count and, for a bundle, positive subconductor spacing. A single
conductor cannot specify bundle spacing. Derived ``bundle_gmr`` and
``equivalent_radius`` are computed from the conductor values. ``GroundWireSpec``
is shared by the geometry's unbundled ground-wire positions.

``CableSpec`` is the common selected-cable value and can carry a
``CatalogReference``. The reference points to a normalized record; it is not a
copy of the raw catalog row.

Routing
-------

``RoutingInfo`` is optional because tower-cross-section electrical parameters
do not require a route. When present, it stores ordered ``Tower`` and
``LineSpan`` component references. There must be at least two towers and
exactly one fewer spans; each span connects consecutive towers. Span length is
derived from endpoint coordinates and elevations when available. Routing does
not alter the electrical calculation documented here.

Electrical parameters and provenance
-------------------------------------

``LineParameters`` aggregates optional electrical and mechanical results.
``ElectricalParameters`` contains named matrices in real/imaginary form,
matrix dimensions and labels, scalar values, units, calculation metadata,
catalog provenance, per-circuit positive-sequence scalars, ampacity and bundle
metadata, and an optional ``StClairResult``. A complete electrical result
contains primitive, Kron-reduced, transposed, and symmetrical-component
matrices. A two-circuit result has six phase rows and separate per-circuit
positive-sequence scalar sets.

``CatalogReference`` records catalog version, table, record identifier, and
optional source identifier. Source artifacts are hashed when the normalized
catalog is generated; runtime models retain compact provenance pointers rather
than raw source rows.

Units, immutability, validation, and serialization
--------------------------------------------------

Embedded engineering values derive from ``LineDataModel``. These Pydantic
values are frozen, reject undeclared fields, and serialize nested Infrasys
quantities with explicit type metadata so units survive JSON round trips.
Registered components such as ``TransmissionLine``, ``Bus``, and
``TowerConfiguration`` retain Infrasys identity. Calculations return copied
line/result values instead of mutating the caller's line; updates follow
``model_copy(update=...)``.

See :doc:`units-and-validation` for units and constraints, and
:doc:`../user-guide/serialization` for system and value-model round trips.