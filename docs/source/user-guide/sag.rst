Cross-section sag
=================

Stage 1 calculates hypothetical sag-versus-horizontal-span curves for each
configured circuit of a ``CrossSectionTransmissionLine``. It does not calculate
routed or time-varying sag, ground clearance, wind/ice loading, hardware offsets,
or evolving creep. Each curve represents one physical subconductor, including
when its phase is bundled; the bundle count does not scale weight, strength, or
area. Results are frozen and external to the input graph.

Inputs and reference state
--------------------------

The selected v2 conductor must have positive ``weight``,
``rated_breaking_strength``, and ``total_material_area`` measurements. Missing
measurements produce circuit- and field-specific errors; v1 equipment does not
gain invented mechanics. Verify the provenance of the selected v2 catalog row.
Callers must supply effective whole-conductor ``ElasticModulus`` and
``ThermalExpansion`` quantities in ``SagOptions``. These are not inferred from
the catalog, and the same options apply to all selected circuits in a call.
Use separate calls when conductors require different effective properties.

``everyday_tension_fraction`` belongs to the line and must be in ``(0, 0.30]``.
When omitted, each conductor uses 20% of its own RBS at the reference state;
the call emits a ``UserWarning`` and records the fallback in the result. The
30% limit applies to reference tension, not solved operating tension.
Reference and operating temperatures default to 25 and 75 degrees Celsius.
Optional nonnegative permanent strain means *additional* strain after the
specified reference state, not creep already reflected in its reference length.

For horizontal span ``l`` and signed end-minus-start attachment rise ``h``, the
pure span solver uses an inclined catenary arc length, an unstressed reference
length, and a temperature-dependent target length. It solves their length
compatibility residual for positive operating horizontal tension, then reports
the maximum vertical sag below the straight attachment chord. The unchanged
reference state with no additional strain retains its known reference tension;
all changed states solve the residual. The curve grid defaults to 20 through
2000 ft, every 10 ft (199 points). Custom endpoints are included exactly, with
a shorter last interval where needed. ``elevation_difference_ft`` defaults to
zero for this hypothetical cross-section and is not a surveyed tower elevation.

Catalog-backed example
----------------------

Run ``python docs/source/how-to/examples/sag_curve.py`` from the repository root.
The example uses a v2 Cardinal conductor; its chosen modulus and expansion
are illustrative effective inputs and must be checked for an actual design.

.. literalinclude:: ../how-to/examples/sag_curve.py
   :language: python