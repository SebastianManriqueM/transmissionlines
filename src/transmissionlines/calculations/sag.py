"""Solve fixed-support catenary sag without route or system dependencies."""

import math
import warnings
from collections.abc import Callable

from transmissionlines.calculations.constants import (
    SAG_GRID_ENDPOINT_TOLERANCE_FT,
    SAG_MAX_BISECTION_STEPS,
    SAG_MAX_BRACKET_STEPS,
    SAG_MAX_CATENARY_SINH_ARGUMENT,
    SAG_MAX_GRID_POINTS,
    SAG_NEGATIVE_DROP_TOLERANCE_FT,
    SAG_POSITION_TOLERANCE_FT,
    SAG_RELATIVE_LENGTH_TOLERANCE,
    SAG_RELATIVE_TENSION_TOLERANCE,
)
from transmissionlines.models.assets import CrossSectionTransmissionLine
from transmissionlines.models.sag import SagCurve, SagCurveResult, SagOptions


def _arc_length(tension_lb: float, weight_lb_ft: float, span_ft: float, rise_ft: float) -> float:
    parameter = tension_lb / weight_lb_ft
    argument = span_ft / (2 * parameter)
    if argument > SAG_MAX_CATENARY_SINH_ARGUMENT:
        raise ValueError("catenary length overflow at trial tension")
    length = math.hypot(2 * parameter * math.sinh(argument), rise_ft)
    if not math.isfinite(length):
        raise ValueError("non-finite catenary length")
    return length


def _bisect_tension(
    residual: Callable[[float], float], reference_tension: float, *, reference_length: float,
) -> float:
    """Find a positive horizontal tension satisfying length compatibility.

    Parameters
    ----------
    residual : callable
        Length compatibility residual in feet for a trial tension in pounds-force.
    reference_tension : float
        Known positive reference-state horizontal tension in pounds-force.
    reference_length : float
        Stressed reference arc length in feet for the relative residual check.

    Returns
    -------
    float
        Solved operating horizontal tension in pounds-force.

    Raises
    ------
    ValueError
        If no finite positive bracket is found or bisection does not converge.
    """
    low = high = reference_tension
    low_residual = high_residual = residual(reference_tension)

    # Expand outward until the decreasing residual brackets zero on both sides.
    for _ in range(SAG_MAX_BRACKET_STEPS):
        if low_residual >= 0:
            break
        low /= 2
        if low <= 0:
            raise ValueError("unable to bracket positive horizontal tension")
        low_residual = residual(low)
    for _ in range(SAG_MAX_BRACKET_STEPS):
        if high_residual <= 0:
            break
        high *= 2
        if not math.isfinite(high):
            raise ValueError("unable to bracket finite horizontal tension")
        high_residual = residual(high)
    if low_residual < 0 or high_residual > 0:
        raise ValueError("unable to bracket horizontal tension")

    # Retain the half-bracket with opposite residual signs until both tolerances hold.
    for _ in range(SAG_MAX_BISECTION_STEPS):
        tension = (low + high) / 2
        difference = residual(tension)
        if difference > 0:
            low = tension
        else:
            high = tension
        if (abs(difference) / reference_length < SAG_RELATIVE_LENGTH_TOLERANCE
            and (high - low) / tension < SAG_RELATIVE_TENSION_TOLERANCE):
            return tension
    raise ValueError("horizontal tension solver did not converge")


def solve_span_sag(
    weight_lb_ft: float,
    rated_strength_lb: float,
    *,
    area_in2: float,
    modulus_psi: float,
    expansion_per_c: float,
    reference_fraction: float,
    span_ft: float,
    rise_ft: float,
    reference_temperature_c: float,
    operating_temperature_c: float,
    additional_permanent_strain: float = 0.0,
) -> tuple[float, float, float]:
    """Solve one physical conductor's maximum chord-relative sag.

    Parameters
    ----------
    weight_lb_ft : float
        Self-weight in pounds-force per foot of conductor arc.
    rated_strength_lb : float
        Rated breaking strength in pounds-force.
    area_in2 : float
        Material cross-sectional area in square inches.
    modulus_psi : float
        Effective elastic modulus in psi.
    expansion_per_c : float
        Effective thermal expansion per degree Celsius.
    reference_fraction : float
        Everyday horizontal tension divided by rated breaking strength.
    span_ft : float
        Horizontal distance between fixed attachments in feet.
    rise_ft : float
        Signed end minus start attachment elevation in feet.
    reference_temperature_c, operating_temperature_c : float
        Conductor temperatures in degrees Celsius.
    additional_permanent_strain : float, optional
        Additional post-reference permanent elongation.

    Returns
    -------
    tuple[float, float, float]
        Maximum chord-relative sag, its horizontal position, and solved
        horizontal tension (ft, ft, lbf).

    Raises
    ------
    ValueError
        If the inputs are invalid or a finite positive root cannot be found.
    """
    numbers = (weight_lb_ft, rated_strength_lb, area_in2, modulus_psi, expansion_per_c,
               reference_fraction, span_ft, rise_ft, reference_temperature_c,
               operating_temperature_c, additional_permanent_strain)
    if not all(math.isfinite(value) for value in numbers):
        raise ValueError("span inputs must be finite")
    if (min(weight_lb_ft, rated_strength_lb, area_in2, modulus_psi, span_ft) <= 0
            or not 0 < reference_fraction <= 0.30 or additional_permanent_strain < 0):
        raise ValueError("span mechanics and length must be positive; reference fraction must be in (0, 0.30]")
    thermal_factor = 1 + expansion_per_c * (operating_temperature_c - reference_temperature_c)
    if not math.isfinite(thermal_factor) or thermal_factor <= 0:
        raise ValueError("invalid thermal expansion factor")
    reference_tension = reference_fraction * rated_strength_lb
    reference_length = _arc_length(reference_tension, weight_lb_ft, span_ft, rise_ft)
    unstressed_length = reference_length / (1 + reference_tension / (modulus_psi * area_in2))

    def residual(tension: float) -> float:
        target = (unstressed_length * (1 + additional_permanent_strain) * thermal_factor
                  * (1 + tension / (modulus_psi * area_in2)))
        value = _arc_length(tension, weight_lb_ft, span_ft, rise_ft) - target
        if not math.isfinite(value):
            raise ValueError("non-finite length compatibility residual")
        return value

    if operating_temperature_c == reference_temperature_c and additional_permanent_strain == 0:
        tension = reference_tension
    else:
        tension = _bisect_tension(residual, reference_tension, reference_length=reference_length)

    parameter = tension / weight_lb_ft
    half_argument = span_ft / (2 * parameter)
    vertex = span_ft / 2 - parameter * math.asinh(rise_ft / (2 * parameter * math.sinh(half_argument)))
    position = vertex + parameter * math.asinh(rise_ft / span_ft)
    if not -SAG_POSITION_TOLERANCE_FT <= position <= span_ft + SAG_POSITION_TOLERANCE_FT:
        raise ValueError("maximum sag position lies outside the span")
    position = min(span_ft, max(0.0, position))
    drop = math.fsum((rise_ft * position / span_ft,
                      -2 * parameter * math.sinh(position / (2 * parameter))
                      * math.sinh((position - 2 * vertex) / (2 * parameter))))
    if not math.isfinite(drop) or drop < -SAG_NEGATIVE_DROP_TOLERANCE_FT:
        raise ValueError("non-finite or negative chord-relative sag")
    return max(0.0, drop), position, tension


def _span_grid(options: SagOptions) -> list[float]:
    start = options.span_start.to("foot").magnitude
    stop = options.span_stop.to("foot").magnitude
    step = options.span_step.to("foot").magnitude
    count = math.floor((stop - start) / step)
    if count > SAG_MAX_GRID_POINTS:
        raise ValueError("span grid exceeds one million points")
    grid = [start + index * step for index in range(count + 1)]
    if grid[-1] < stop and not math.isclose(grid[-1], stop, abs_tol=SAG_GRID_ENDPOINT_TOLERANCE_FT):
        grid.append(stop)
    else:
        grid[-1] = stop
    return grid


def calculate_sag(
    line: CrossSectionTransmissionLine,
    *,
    options: SagOptions,
    circuit_id: str | None = None,
) -> SagCurveResult:
    """Calculate hypothetical cross-section sag curves for selected circuits.

    Parameters
    ----------
    line : CrossSectionTransmissionLine
        Source of circuit selections and everyday reference tension.
    options : SagOptions
        Required effective material properties, temperatures, and span grid.
    circuit_id : str, optional
        Select one circuit; by default calculate every configured circuit.

    Returns
    -------
    SagCurveResult
        Frozen external curves with one representative subconductor per circuit.

    Raises
    ------
    ValueError
        If a circuit or required conductor measurement is missing, or solving fails.
    """
    if not isinstance(line, CrossSectionTransmissionLine):
        raise TypeError("calculate_sag requires a CrossSectionTransmissionLine")
    circuits = sorted(line.configuration.circuits, key=lambda circuit: circuit.circuit_id)
    if circuit_id is not None:
        circuits = [circuit for circuit in circuits if circuit.circuit_id == circuit_id]
        if not circuits:
            raise ValueError(f"unknown circuit_id {circuit_id!r} for line {line.name}")
    fallback = line.everyday_tension_fraction is None
    fraction = 0.20 if fallback else line.everyday_tension_fraction
    messages: list[str] = []
    if fallback:
        message = f"line {line.name}: everyday tension omitted; using 20% of each conductor's RBS"
        warnings.warn(message, UserWarning, stacklevel=2)
        messages.append(message)
    grid = _span_grid(options)
    curves = []
    for circuit in circuits:
        equipment = circuit.conductor_spec.equipment
        for field in ("weight", "rated_breaking_strength", "total_material_area"):
            measurement = getattr(equipment, field)
            if measurement is None or not math.isfinite(measurement.magnitude) or measurement.magnitude <= 0:
                raise ValueError(f"line {line.name} circuit {circuit.circuit_id}: {field} must be present and positive")
        sag, tensions = [], []
        for span in grid:
            try:
                value, _, tension = solve_span_sag(
                    equipment.weight.to("pound_force / foot").magnitude,
                    equipment.rated_breaking_strength.to("pound_force").magnitude,
                    area_in2=equipment.total_material_area.to("inch ** 2").magnitude,
                    modulus_psi=options.elastic_modulus.to("psi").magnitude,
                    expansion_per_c=options.thermal_expansion_coefficient.to("1 / kelvin").magnitude,
                    reference_fraction=fraction,
                    span_ft=span, rise_ft=options.elevation_difference.to("foot").magnitude,
                    reference_temperature_c=options.reference_temperature.to("degC").magnitude,
                    operating_temperature_c=options.operating_temperature.to("degC").magnitude,
                    additional_permanent_strain=options.additional_permanent_strain,
                )
            except ValueError as error:
                raise ValueError(f"line {line.name} circuit {circuit.circuit_id} span {span:g} ft: {error}") from error
            sag.append(value)
            tensions.append(tension)
        curves.append(SagCurve(circuit_id=circuit.circuit_id, conductor_uuid=circuit.conductor_spec.uuid,
                               span_lengths_ft=grid, sag_ft=sag, horizontal_tension_lb=tensions))
    return SagCurveResult(line_uuid=line.uuid, line_name=line.name, options=options,
                          everyday_tension_fraction=fraction, used_default_everyday_tension=fallback,
                          curves=curves, warnings=messages)