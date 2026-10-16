"""Pure Julia-parity electrical calculation orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from collections.abc import Mapping, Sequence
from math import log, pi
from typing import Any

import numpy as np

from transmissionlines.bundle import derived_bundle_values
from transmissionlines.calculations.cable import ground_wire_gmr
from transmissionlines.calculations.geometry import pairwise_distances, pairwise_image_distances
from transmissionlines.calculations.input_resolver import resolve_configuration
from transmissionlines.calculations.matrices import (
    fully_transpose,
    kron_reduce,
    sequence_matrix,
    shunt_admittance,
)
from transmissionlines.calculations.st_clair import calculate_st_clair
from transmissionlines.electrical_constants import EPSILON_AIR, KILOFEET_PER_MILE, L_C, L_F, R_C
from transmissionlines.models.assets import CrossSectionTransmissionLine, RoutedTransmissionLine
from transmissionlines.models.calculation_result import LineCalculationResult
from transmissionlines.models.cables import GroundWireSpec
from transmissionlines.models.configurations import CircuitConfiguration, TowerConfiguration
from transmissionlines.models.electrical import ElectricalParameters, MatrixResult
from transmissionlines.models.routing import ElectricalTower
from transmissionlines.models.st_clair import StClairOptions, StClairResult
from transmissionlines.models.geometry import CablePosition, TowerGeometry

def _matrix_result(
    name: str,
    matrix: np.ndarray,
    *,
    unit: str,
    labels: list[str],
) -> MatrixResult:
    """Convert a NumPy result into an explicitly typed JSON-safe matrix."""
    value = np.asarray(matrix, dtype=complex)
    return MatrixResult(
        name=name,
        row_count=value.shape[0],
        column_count=value.shape[1],
        row_labels=list(labels),
        column_labels=list(labels),
        unit=unit,
        real=value.real.tolist(),
        imaginary=value.imag.tolist(),
    )


def build_primitive_z(
    positions: list[CablePosition],
    *,
    gmrs: list[float],
    resistances: list[float],
    bundle_counts: list[int],
    frequency: float,
    earth_resistivity: float,
) -> np.ndarray:
    r"""Build the primitive series impedance matrix in ohm/mile (modified Carson).

    .. math::
        z_{ii} &= \frac{r_i}{n_i} + R_C f + j L_C f \left( \ln\frac{1}{\mathrm{GMR}_i} + L_F
                  + \tfrac12 \ln\frac{\rho}{f} \right) \\
        z_{ij} &= R_C f + j L_C f \left( \ln\frac{1}{D_{ij}} + L_F + \tfrac12 \ln\frac{\rho}{f} \right)

    with :math:`D_{ij}` and :math:`\mathrm{GMR}_i` in feet, :math:`r_i` in ohm/mile,
    :math:`n_i` subconductors in parallel, and the coefficients derived in
    :mod:`transmissionlines.electrical_constants`. At 60 Hz and 100 ohm-m this is
    the familiar :math:`z_{ii} = r_i + 0.09530 + j\,0.12134 (\ln(1/\mathrm{GMR}_i) + 7.93402)`.

    Parameters
    ----------
    positions : list of CablePosition
        Ordered phase and ground-wire coordinates.
    gmrs : list of float
        Self GMR values in feet, one per position.
    resistances : list of float
        Selected phase AC or ground-wire DC resistances in ohm/kilofoot.
    bundle_counts : list of int
        Number of subconductors represented by each position.
    frequency : float
        System frequency in hertz.
    earth_resistivity : float
        Earth resistivity in ohm-meter.

    Returns
    -------
    numpy.ndarray
        Complex square primitive series matrix in ohm/mile.
    """
    distances = pairwise_distances(positions)
    np.fill_diagonal(distances, gmrs)
    resistance = np.diag(np.asarray(resistances) / np.asarray(bundle_counts) * KILOFEET_PER_MILE)
    correction = L_F + 0.5 * log(earth_resistivity / frequency)
    return resistance + R_C * frequency + 1j * L_C * frequency * (np.log(1 / distances) + correction)


def build_primitive_p(positions: list[CablePosition], *, radii: list[float]) -> np.ndarray:
    r"""Build the primitive potential-coefficient matrix in mile/µF (method of images).

    Each conductor :math:`i` has an image at the mirrored height below ground, at
    distance :math:`S_{ij}` from conductor :math:`j`:

    .. math::
        P_{ii} = \frac{1}{2\pi\varepsilon} \ln\frac{S_{ii}}{r_i}, \qquad
        P_{ij} = \frac{1}{2\pi\varepsilon} \ln\frac{S_{ij}}{D_{ij}},

    where :math:`S_{ii} = 2 h_i`, :math:`r_i` is the (equivalent) conductor radius,
    and :math:`1/(2\pi\varepsilon) = 11.17689` mile/µF.

    Parameters
    ----------
    positions : list of CablePosition
        Ordered phase and ground-wire coordinates in feet.
    radii : list of float
        Equivalent phase radii or physical ground-wire radii in feet.

    Returns
    -------
    numpy.ndarray
        Real square potential coefficient matrix using the parity
        ``1/(microSiemens/mile)`` contract.
    """
    direct = pairwise_distances(positions)
    np.fill_diagonal(direct, radii)
    return np.log(pairwise_image_distances(positions) / direct) / (2 * pi * EPSILON_AIR)


def _ordered_inputs(
    geometry: TowerGeometry,
    phase_specs: dict[str, CircuitConfiguration],
    ground_spec: GroundWireSpec,
) -> tuple[list[CablePosition], list[float], list[float], list[float], list[int], list[str], int]:
    circuit_order = list(dict.fromkeys(p.circuit_id for p in geometry.phase_positions))
    phase_order = {phase: index for index, phase in enumerate(("A", "B", "C"))}
    phases = sorted(geometry.phase_positions, key=lambda p: (circuit_order.index(p.circuit_id), phase_order[p.phase]))
    grounds = sorted(geometry.ground_wire_positions, key=lambda p: p.wire_id)
    positions: list[CablePosition] = list(phases) + list(grounds)
    gmrs: list[float] = []
    radii: list[float] = []
    resistances: list[float] = []
    counts: list[int] = []
    labels = [f"{p.circuit_id}:{p.phase}" for p in phases] + [f"ground:{p.wire_id}" for p in grounds]
    for phase in phases:
        spec = phase_specs[phase.circuit_id]
        conductor = spec.conductor_spec.equipment
        bundle_gmr, equivalent_radius = derived_bundle_values(
            conductor, spec.bundle_spec.subconductor_count, spec.bundle_spec.subconductor_spacing_in
        )
        if bundle_gmr is None or equivalent_radius is None or conductor.ac_resistance_ohm_kft is None:
            raise ValueError(f"missing required conductor value for circuit {phase.circuit_id}")
        gmrs.append(bundle_gmr)
        radii.append(equivalent_radius)
        resistances.append(conductor.ac_resistance_ohm_kft)
        counts.append(spec.bundle_spec.subconductor_count)
    ground = ground_spec.equipment
    if ground.diameter_in is None or ground.dc_resistance_ohm_kft is None:
        raise ValueError("ground wire requires diameter and dc_resistance")
    for _ in grounds:
        gmrs.append(ground_wire_gmr(ground.diameter_in))
        radii.append(ground.diameter_in / 24.0)
        resistances.append(ground.dc_resistance_ohm_kft)
        counts.append(1)
    return positions, gmrs, radii, resistances, counts, labels, len(phases)


def calculate_line_electrical_parameters(
    line: CrossSectionTransmissionLine | RoutedTransmissionLine,
    *, tower: ElectricalTower | None = None, st_clair_options: StClairOptions | None = None,
) -> LineCalculationResult:
    """Calculate transient electrical and St. Clair results for one cross-section.

    A routed line with different installed configurations requires a selected
    tower. Its result describes that tower's cross-section, never an aggregate
    impedance or loadability curve for the full route.

    Parameters
    ----------
    line : CrossSectionTransmissionLine or RoutedTransmissionLine
        Registered static electrical inputs.
    tower : ElectricalTower, optional
        Line-owned support required for a heterogeneous routed line.
    st_clair_options : StClairOptions, optional
        Operating limits and curve resolution, independent of route length.

    Returns
    -------
    LineCalculationResult
        Standalone matrices and curves identified by line and configuration.

    Raises
    ------
    ValueError
        If selection is ambiguous or foreign, or required cable values are absent.
    """
    configuration = resolve_configuration(line, tower=tower)
    electrical = _line_electrical(line, configuration)
    curve = calculate_st_clair(_st_clair_inputs(line, configuration, electrical), options=st_clair_options)
    return LineCalculationResult(
        line_name=line.name, electrical=electrical, st_clair=curve.model_copy(update={"line_name": line.name}),
    )


def calculate_st_clair_curve_for_line(
    line: CrossSectionTransmissionLine | RoutedTransmissionLine,
    *,
    tower: ElectricalTower | None = None,
    options: StClairOptions | None = None,
    sensitivities: Mapping[str, Sequence[float]] | None = None,
) -> StClairResult:
    """Calculate St. Clair curves for a line's selected cross-section.

    The positive-sequence constants are calculated from the line itself, so the
    curves always describe its current configuration.

    Parameters
    ----------
    line : CrossSectionTransmissionLine or RoutedTransmissionLine
        Static input line.
    tower : ElectricalTower, optional
        Support selecting a heterogeneous routed cross-section.
    options : StClairOptions, optional
        Curve operating limits and resolution.
    sensitivities : mapping, optional
        Option names and sampled settings for extra curves.

    Raises
    ------
    ValueError
        If the cross-section selection is ambiguous or foreign, or a circuit's
        conductor lacks a required value.
    """
    configuration = resolve_configuration(line, tower=tower)
    inputs = _st_clair_inputs(line, configuration, _line_electrical(line, configuration))
    result = calculate_st_clair(inputs, options=options, sensitivities=sensitivities)
    return result.model_copy(update={"line_name": line.name})


def _line_electrical(
    line: CrossSectionTransmissionLine | RoutedTransmissionLine, configuration: TowerConfiguration,
) -> ElectricalParameters:
    return calculate_electrical(
        configuration.geometry,
        phase_specs=configuration.circuits,
        ground_wire_spec=configuration.ground_wire_spec,
        voltage_kv=line.nominal_voltage_kv,
        frequency_hz=line.nominal_frequency_hz,
        earth_resistivity_ohm_m=line.earth_resistivity_ohm_m,
    )


def _st_clair_inputs(
    line: CrossSectionTransmissionLine | RoutedTransmissionLine,
    configuration: TowerConfiguration,
    electrical: ElectricalParameters,
) -> list[dict[str, Any]]:
    """Pair each circuit's positive-sequence constants with its conductor ampacity."""
    inputs = []
    for spec in configuration.circuits:
        equipment = spec.conductor_spec.equipment
        if equipment.ampacity_a is None:
            raise ValueError(f"missing conductor ampacity for {spec.circuit_id}")
        scalars = electrical.circuit_scalars[spec.circuit_id]
        inputs.append({
            "circuit_id": spec.circuit_id,
            "conductor_family": spec.conductor_spec.family,
            "conductor_codeword": spec.conductor_spec.codeword,
            "nominal_voltage_kv": line.nominal_voltage_kv,
            "r_ohm_per_mile": scalars["r1"],
            "x_ohm_per_mile": scalars["x1"],
            "b_microsiemens_per_mile": scalars["b1"],
            "conductor_ampacity_a": equipment.ampacity_a,
            "subconductor_count": spec.bundle_spec.subconductor_count,
        })
    return inputs


def calculate_electrical_parameters(
    line: CrossSectionTransmissionLine | RoutedTransmissionLine,
    *, tower: ElectricalTower | None = None,
) -> LineCalculationResult:
    """Calculate standalone electrical parameters and a default curve.

    Parameters
    ----------
    line : CrossSectionTransmissionLine or RoutedTransmissionLine
        Static inputs for the selected cross-section.
    tower : ElectricalTower, optional
        Required support when routed configurations differ.

    Returns
    -------
    LineCalculationResult
        External result envelope; the input line is unchanged.
    """
    return calculate_line_electrical_parameters(line, tower=tower)


def calculate_electrical(
    geometry: TowerGeometry,
    *,
    phase_specs: list[CircuitConfiguration],
    ground_wire_spec: GroundWireSpec,
    voltage_kv: float,
    frequency_hz: float,
    earth_resistivity_ohm_m: float,
) -> ElectricalParameters:
    """Calculate all Julia-parity electrical result matrices and scalars.

    Parameters
    ----------
    geometry : TowerGeometry
        Tower-local phase and ground-wire positions.
    phase_specs : list of CircuitConfiguration
        One conductor/bundle specification per geometry circuit.
    ground_wire_spec : GroundWireSpec
        Shared ground-wire conductor properties.
    voltage_kv, frequency_hz, earth_resistivity_ohm_m : float
        Nominal line-to-line voltage, power frequency, and earth resistivity.

    Returns
    -------
    ElectricalParameters
        Completed, JSON-safe primitive/reduced/transposed matrices and scalar
        sequence values, without an attached St. Clair curve.

    Raises
    ------
    ValueError
        If required physical cable values are absent, or the geometry has more
        than two circuits.
    """
    specs = {spec.circuit_id: spec for spec in phase_specs}
    positions, gmrs, radii, resistances, counts, labels, phase_count = _ordered_inputs(geometry, specs, ground_wire_spec)
    ground_count = len(geometry.ground_wire_positions)
    z_primitive = build_primitive_z(positions, gmrs=gmrs, resistances=resistances, bundle_counts=counts, frequency=frequency_hz, earth_resistivity=earth_resistivity_ohm_m)
    p_primitive = build_primitive_p(positions, radii=radii)
    z_kron = kron_reduce(z_primitive, phase_count, ground_count)
    p_kron = kron_reduce(p_primitive, phase_count, ground_count)
    y_kron = shunt_admittance(p_kron, frequency_hz)
    z_sequence_nt = sequence_matrix(z_kron)
    y_sequence_nt = sequence_matrix(y_kron)
    circuits = phase_count // 3
    if circuits > 2:
        raise ValueError(f"only one- and two-circuit lines are supported, got {circuits} circuits")
    z_transposed = fully_transpose(z_kron)
    y_transposed = fully_transpose(y_kron)
    z_sequence = sequence_matrix(z_transposed)
    y_sequence = sequence_matrix(y_transposed)
    circuit_ids = list(dict.fromkeys(position.circuit_id for position in geometry.phase_positions))
    circuit_scalars = {
        circuit_ids[index]: {
            "r1": float(z_sequence[index * 3 + 1, index * 3 + 1].real),
            "x1": float(z_sequence[index * 3 + 1, index * 3 + 1].imag),
            "b1": float(y_sequence[index * 3 + 1, index * 3 + 1].imag),
        }
        for index in range(circuits)
    }
    r1, x1, b1 = (circuit_scalars[circuit_ids[0]][name] for name in ("r1", "x1", "b1"))
    # Lossless surge impedance Z_c = sqrt(L/C) = sqrt(x1 / b1); SIL = V_LL^2 / Z_c (kV^2 / ohm = MW).
    z_sil = (x1 / (b1 / 1e6)) ** 0.5
    scalars = {"r1": float(r1), "x1": float(x1), "b1": float(b1), "r0": float(z_sequence[0, 0].real), "x0": float(z_sequence[0, 0].imag), "b0": float(y_sequence[0, 0].imag), "surge_impedance_ohm": float(z_sil), "sil_mw": float(voltage_kv**2 / z_sil)}
    if circuits == 2:
        scalars.update({"r0_mutual": float(z_sequence[3, 0].real), "x0_mutual": float(z_sequence[3, 0].imag), "b0_mutual": float(y_sequence[3, 0].imag)})
    phase_labels = labels[:phase_count]
    sequence_labels = [
        f"{circuit}:{sequence}"
        for circuit in range(1, circuits + 1)
        for sequence in ("zero", "positive", "negative")
    ]
    matrices = {
        "Zabcg": _matrix_result("Zabcg", z_primitive, unit="ohm/mile", labels=labels),
        "Pabcg": _matrix_result("Pabcg", p_primitive, unit="1/(microSiemens/mile)", labels=labels),
        "Z_kron_nt": _matrix_result("Z_kron_nt", z_kron, unit="ohm/mile", labels=phase_labels),
        "P_kron_nt": _matrix_result("P_kron_nt", p_kron, unit="1/(microSiemens/mile)", labels=phase_labels),
        "Y_kron_nt": _matrix_result("Y_kron_nt", y_kron, unit="microsiemens/mile", labels=phase_labels),
        "Z012_nt": _matrix_result("Z012_nt", z_sequence_nt, unit="ohm/mile", labels=sequence_labels),
        "Y012_nt": _matrix_result("Y012_nt", y_sequence_nt, unit="microsiemens/mile", labels=sequence_labels),
        "Z_kron_ft": _matrix_result("Z_kron_ft", z_transposed, unit="ohm/mile", labels=phase_labels),
        "Y_kron_ft": _matrix_result("Y_kron_ft", y_transposed, unit="microsiemens/mile", labels=phase_labels),
        "Z012_ft": _matrix_result("Z012_ft", z_sequence, unit="ohm/mile", labels=sequence_labels),
        "Y012_ft": _matrix_result("Y012_ft", y_sequence, unit="microsiemens/mile", labels=sequence_labels),
    }
    matrices.update({
        "Z_primitive": matrices["Zabcg"], "P_primitive": matrices["Pabcg"],
        "Z_kron": matrices["Z_kron_nt"], "P_kron": matrices["P_kron_nt"], "Y_kron": matrices["Y_kron_nt"],
        "Z_transposed": matrices["Z_kron_ft"], "Y_transposed": matrices["Y_kron_ft"],
        "Z_sequence": matrices["Z012_ft"], "Y_sequence": matrices["Y012_ft"],
    })
    provenance = [
        spec.conductor_spec.catalog_reference.model_dump()
        for spec in phase_specs
        if spec.conductor_spec.catalog_reference is not None
    ]
    if ground_wire_spec.catalog_reference is not None:
        provenance.append(ground_wire_spec.catalog_reference.model_dump())
    scalar_units = {
        "r1": "ohm/mile", "x1": "ohm/mile", "r0": "ohm/mile", "x0": "ohm/mile",
        "b1": "microsiemens/mile", "b0": "microsiemens/mile",
        "surge_impedance_ohm": "ohm", "sil_mw": "MW",
    }
    if circuits == 2:
        scalar_units.update({"r0_mutual": "ohm/mile", "x0_mutual": "ohm/mile", "b0_mutual": "microsiemens/mile"})
    return ElectricalParameters(
        labels=labels,
        matrices=matrices,
        scalars=scalars,
        scalar_units=scalar_units,
        circuit_scalars=circuit_scalars,
        circuit_scalar_units={
            key: {"r1": "ohm/mile", "x1": "ohm/mile", "b1": "microsiemens/mile"}
            for key in circuit_scalars
        },
        circuit_ampacity_a={
            spec.circuit_id: spec.conductor_spec.equipment.ampacity_a
            for spec in phase_specs if spec.conductor_spec.equipment.ampacity_a is not None
        },
        circuit_subconductor_count={
            spec.circuit_id: spec.bundle_spec.subconductor_count for spec in phase_specs
        },
        provenance=provenance,
        topology="one-circuit" if circuits == 1 else "two-circuit",
        status="complete",
        calculated_at=datetime.now(UTC),
    )


__all__ = ["EPSILON_AIR", "L_C", "L_F", "R_C", "build_primitive_p", "build_primitive_z", "calculate_electrical", "calculate_electrical_parameters", "calculate_line_electrical_parameters", "calculate_st_clair_curve_for_line", "resolve_configuration"]
