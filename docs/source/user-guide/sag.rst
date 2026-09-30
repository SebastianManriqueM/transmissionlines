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
``reference_temperature`` and ``operating_temperature`` require ``Temperature``
quantities (for example, degrees Celsius, Fahrenheit, or kelvin). ``span_start``,
``span_stop``, ``span_step``, and signed ``elevation_difference`` require
``SpanLength`` quantities (for example, feet or metres). Bare numbers are
rejected for all physical options. ``additional_permanent_strain`` is a
dimensionless float. The calculation converts temperature to degrees Celsius
and lengths to feet before calling the pure single-conductor solver.

``everyday_tension_fraction`` belongs to the line and must be in ``(0, 0.30]``.
When omitted, each conductor uses 20% of its own RBS at the reference state;
the call emits a ``UserWarning`` and records the fallback in the result. The
30% limit applies to reference tension, not solved operating tension.
Reference and operating temperatures default to 25 and 75 degrees Celsius.
Optional nonnegative permanent strain means *additional* strain after the
specified reference state, not creep already reflected in its reference length.

The curve grid defaults to 20 through 2000 ft, every 10 ft (199 points).
Custom endpoints are included exactly, with a shorter last interval where
needed. ``elevation_difference`` defaults to zero feet for this hypothetical
cross-section and is not a surveyed tower elevation.

Sag models and notation
-----------------------

``SagOptions`` validates the effective whole-conductor properties, temperatures,
span grid, signed support-height difference, and additional permanent strain.
``calculate_sag`` reads one physical conductor per selected circuit and converts
its measured properties and the options to the solver's units. The independent
``solve_span_sag`` function uses plain numbers, with no route or Infrasys
dependencies. ``SagCurve`` holds parallel horizontal-span, maximum-sag, and
horizontal-tension arrays for one circuit; ``SagCurveResult`` stores the curves,
the options, source identities, and any reference-tension fallback warning
outside the registered line graph.

The equations use the following quantities for a single physical conductor:

``D`` (ft)
   Positive horizontal attachment separation.
``h`` (ft)
   Signed end-minus-start attachment rise; either support may be higher.
``w`` (lbf/ft)
   Conductor self-weight per foot of conductor arc.
``H`` (lbf), ``a = H/w`` (ft)
   Trial horizontal tension and its catenary parameter.
``RBS`` (lbf), ``r`` (dimensionless)
   Rated breaking strength and reference everyday tension fraction.
``E`` (psi), ``A`` (inches squared)
   Effective whole-conductor elastic modulus and material area.
``alpha`` (per degree Celsius)
   Effective whole-conductor thermal expansion coefficient.
``T_ref``, ``T_op`` (degrees Celsius)
   Reference and operating conductor temperatures.
``epsilon_p`` (dimensionless)
   Additional permanent strain after the reference state.
``x`` (ft)
   Horizontal position measured from the start attachment.

Reference length and operating tension
--------------------------------------

For fixed supports, the exact inclined catenary arc length at trial tension
:math:`H` is

.. math::

   L(H) = \sqrt{\left[2a\sinh\left(\frac{D}{2a}\right)\right]^2+h^2},
   \qquad a=\frac{H}{w}.

The known reference horizontal tension is :math:`H_{\mathrm{ref}}=r\,RBS`.
The solver removes reference elastic strain to obtain the unstressed length:

.. math::

   L_{\mathrm{ref}} = L(H_{\mathrm{ref}}), \qquad
   L_0 = \frac{L_{\mathrm{ref}}}{1+H_{\mathrm{ref}}/(EA)}.

The thermal factor must remain positive. At operating temperature and trial
tension, the target stressed length and compatibility residual are

.. math::

   \begin{aligned}
   f_T &= 1+\alpha(T_{\mathrm{op}}-T_{\mathrm{ref}}), \\
   L_{\mathrm{target}}(H) &= L_0(1+\epsilon_p)f_T
       \left(1+\frac{H}{EA}\right), \\
   F(H) &= L(H)-L_{\mathrm{target}}(H)=0.
   \end{aligned}

Added permanent strain changes the operating length even when the temperatures
are equal. Only when :math:`T_{\mathrm{op}}=T_{\mathrm{ref}}` **and**
:math:`\epsilon_p=0` does the solver reuse :math:`H_{\mathrm{ref}}` directly.
Otherwise it solves for a positive operating :math:`H`; the 30% RBS cap is
not applied to this solved tension.

Bisection algorithm
-------------------

The residual decreases with increasing positive tension. Starting at
:math:`H_{\mathrm{ref}}`, the solver halves the lower trial tension while its
residual is negative and doubles the upper trial tension while its residual is
positive. It requires a finite positive bracket with
:math:`F(H_{\mathrm{low}})\geq 0` and
:math:`F(H_{\mathrm{high}})\leq 0`; each direction allows at most 1024
expansions. Each bisection evaluates :math:`F` at the bracket midpoint. A
positive residual replaces the lower bound; otherwise the upper bound is
replaced. Convergence requires **both**

.. math::

   \frac{|F(H)|}{L_{\mathrm{ref}}}<10^{-11}, \qquad
   \frac{H_{\mathrm{high}}-H_{\mathrm{low}}}{H}<10^{-10}.

At most 256 midpoint iterations are allowed. A non-finite length, overflow,
failure to bracket a positive tension, or failure to converge raises an error
with the line, circuit, and span when called through ``calculate_sag``.

Chord-relative maximum sag
--------------------------

For the solved :math:`a=H/w`, the catenary vertex and the stationary point of
the vertical distance below the straight line between attachments are

.. math::

   \begin{aligned}
   x_v &= \frac{D}{2}-a\,\mathrm{asinh}\!\left(
       \frac{h}{2a\sinh(D/(2a))}\right), \\
   x_{*} &= x_v+a\,\mathrm{asinh}\!\left(\frac{h}{D}\right).
   \end{aligned}

The straight attachment chord has height :math:`hx/D` above the start
attachment. Subtracting the catenary height gives the maximum vertical sag:

.. math::

   s_{\max}=\frac{h x_{*}}{D}-a\left[
       \cosh\!\left(\frac{x_{*}-x_v}{a}\right)
       -\cosh\!\left(\frac{x_v}{a}\right)\right].

The implementation evaluates the hyperbolic difference as
:math:`2\sinh(x_{*}/(2a))\sinh((x_{*}-2x_v)/(2a))` to reduce
cancellation. It rejects a stationary point outside the horizontal span and
clamps only tiny endpoint or negative-drop roundoff. For level supports,
:math:`h=0`, :math:`x_{*}=D/2` and
:math:`s_{\max}=a[\cosh(D/(2a))-1]`. The reported value is the **maximum
vertical drop below the attachment chord**, not the drop below either support.

Catalog-backed example
----------------------

Run ``python docs/source/how-to/examples/sag_curve.py`` from the repository root.
The example uses a v2 Cardinal conductor; its chosen modulus and expansion
are illustrative effective inputs and must be checked for an actual design.

.. literalinclude:: ../how-to/examples/sag_curve.py
   :language: python