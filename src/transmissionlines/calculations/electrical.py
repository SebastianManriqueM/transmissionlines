"""Pure Julia-parity electrical calculation orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from math import log, pi
from typing import TYPE_CHECKING

import numpy as np

from transmissionlines.calculations.cable import ground_wire_gmr
from transmissionlines.calculations.geometry import direct_distance, image_distance
from transmissionlines.calculations.matrices import (
    fully_transpose,
    kron_reduce,
    sequence_matrix,
    shunt_admittance,
)
from transmissionlines.calculations.st_clair import calculate_st_clair_curve_for_line
from transmissionlines.exceptions import CalculationInputError
from transmissionlines.models.cables import GroundWireSpec, PhaseConductorSpec
from transmissionlines.models.electrical import ElectricalParameters, MatrixResult
from transmissionlines.models.parameters import LineParameters
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.models.geometry import CablePosition, TowerGeometry
from transmissionlines.units import Frequency, VoltageKV

if TYPE_CHECKING:
    from transmissionlines.models.assets import TransmissionLine

R_C = 0.00158836
L_C = 0.00202237
L_F = 7.6786
EPSILON_AIR = 1.4240e-2


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
    """Build the primitive series impedance matrix in ohm/mile.

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

    Raises
    ------
    ValueError
        If array lengths differ or required physical inputs are not positive.
    """
    n = len(positions)
    if n < 1 or not (len(gmrs) == len(resistances) == len(bundle_counts) == n):
        raise ValueError("primitive Z inputs must have equal non-empty lengths")
    if any(gmr <= 0 for gmr in gmrs) or any(count < 1 for count in bundle_counts):
        raise ValueError("GMR values must be positive and bundle counts must be positive")
    if frequency <= 0 or earth_resistivity <= 0:
        raise ValueError("frequency and earth resistivity must be positive")
    result = np.zeros((n, n), dtype=complex)
    correction = L_F + 0.5 * log(earth_resistivity / frequency)
    for i, position in enumerate(positions):
        for j in range(i, n):
            if i == j:
                distance = gmrs[i]
                resistance = resistances[i] / bundle_counts[i] * 5.28
            else:
                distance = direct_distance(position, positions[j])
                resistance = 0.0
            if distance <= 0:
                raise ValueError("all conductor GMR and mutual distances must be positive")
            value = resistance + R_C * frequency + 1j * L_C * frequency * (log(1 / distance) + correction)
            result[i, j] = result[j, i] = value
    return result


def build_primitive_p(
    positions: list[CablePosition],
    *,
    radii: list[float],
    frequency: float,
) -> np.ndarray:
    """Build the primitive potential matrix in the Julia micro-unit contract.

    Parameters
    ----------
    positions : list of CablePosition
        Ordered phase and ground-wire coordinates in feet.
    radii : list of float
        Equivalent phase radii or physical ground-wire radii in feet.
    frequency : float
        Retained for the calculation interface; the potential formula does not
        use frequency.

    Returns
    -------
    numpy.ndarray
        Real square potential coefficient matrix using the parity
        ``1/(microSiemens/mile)`` contract.

    Raises
    ------
    ValueError
        If positions and radii differ in length or any radius is not positive.
    """
    del frequency  # retained in the signature to make the unit boundary explicit
    if not positions or len(radii) != len(positions):
        raise ValueError("potential radii and positions must have equal non-empty lengths")
    if any(radius <= 0 for radius in radii):
        raise ValueError("potential radii must be positive")
    result = np.zeros((len(positions), len(positions)), dtype=float)
    for i, position in enumerate(positions):
        result[i, i] = log(image_distance(position, position) / radii[i]) / (2 * pi * EPSILON_AIR)
        for j in range(i):
            value = log(image_distance(position, positions[j]) / direct_distance(position, positions[j])) / (2 * pi * EPSILON_AIR)
            result[i, j] = result[j, i] = value
    return result


def _ordered_inputs(
    geometry: TowerGeometry,
    phase_specs: dict[str, PhaseConductorSpec],
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
        if spec.bundle_gmr is None or spec.equivalent_radius is None or spec.conductor.ac_resistance is None:
            raise ValueError(f"missing required conductor value for circuit {phase.circuit_id}")
        gmrs.append(spec.bundle_gmr.to("foot").magnitude)
        radii.append(spec.equivalent_radius.to("foot").magnitude)
        resistances.append(spec.conductor.ac_resistance.to("ohm / kilofoot").magnitude)
        counts.append(spec.subconductor_count)
    if ground_spec.conductor.conductor_diameter is None or ground_spec.conductor.dc_resistance is None:
        raise ValueError("ground wire requires diameter and dc_resistance")
    for _ in grounds:
        diameter = ground_spec.conductor.conductor_diameter.to("inch").magnitude
        gmrs.append(ground_wire_gmr(diameter))
        radii.append(diameter / 24.0)
        resistances.append(ground_spec.conductor.dc_resistance.to("ohm / kilofoot").magnitude)
        counts.append(1)
    return positions, gmrs, radii, resistances, counts, labels, len(phases)


def calculate_line_electrical_parameters(
    line: TransmissionLine, *, st_clair_options: StClairOptions | None = None
) -> TransmissionLine:
    """Return a copied line with electrical and default St. Clair results.

    Routing is deliberately not consulted: v3 electrical parameters describe
    the tower cross-section and terminal technical inputs only. The source line
    and any existing mechanical result remain unchanged.

    Parameters
    ----------
    line : TransmissionLine
        Line with validated technical information, tower geometry, and cable
        specifications.
    st_clair_options : StClairOptions, optional
        Operating limits and sweep resolution. When omitted, default St. Clair
        settings are used.

    Returns
    -------
    TransmissionLine
        New line value with complete electrical matrices/scalars and its
        St. Clair result attached. The input line is unchanged.

    Raises
    ------
    CalculationInputError
        If phase-conductor specifications do not match geometry circuits.
    ValueError
        If required conductor or ground-wire calculation values are absent or
        invalid.
    """
    geometry = line.tower_configuration.geometry
    geometry_ids = {position.circuit_id for position in geometry.phase_positions}
    specs = line.tower_configuration.phase_conductor_specs
    spec_ids = [spec.circuit_id for spec in specs]
    spec_id_set = set(spec_ids)
    missing = sorted(geometry_ids - spec_id_set)
    unexpected = sorted(spec_id_set - geometry_ids)
    duplicates = sorted({item for item in spec_ids if spec_ids.count(item) > 1})
    if missing or unexpected or duplicates:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if unexpected:
            details.append(f"unexpected={unexpected}")
        if duplicates:
            details.append(f"duplicates={duplicates}")
        raise CalculationInputError("phase conductor circuit mapping is invalid: " + ", ".join(details))
    technical = line.technical_info
    result = calculate_electrical(
        geometry,
        phase_specs=specs,
        ground_wire_spec=line.tower_configuration.ground_wire_spec,
        voltage=technical.nominal_voltage.to("kilovolt"),
        frequency=technical.nominal_frequency.to("hertz"),
        earth_resistivity=technical.earth_resistivity.to("ohm * meter").magnitude,
    )
    result = calculate_st_clair_curve_for_line(
        line.model_copy(update={"line_parameters": LineParameters(electrical_parameters=result)}),
        options=st_clair_options,
    )
    parameters = line.line_parameters or LineParameters()
    result = result.line_parameters.electrical_parameters
    assert result is not None
    updated_parameters = parameters.model_copy(update={"electrical_parameters": result})
    return line.model_copy(update={"line_parameters": updated_parameters})


def calculate_electrical_parameters(line: TransmissionLine) -> TransmissionLine:
    """Return line electrical results using the current orchestration defaults.

    This backward-compatible alias calculates electrical parameters and the
    default St. Clair curve. Use :func:`calculate_line_electrical_parameters`
    to provide explicit St. Clair options.

    Parameters
    ----------
    line : TransmissionLine
        Validated line input.

    Returns
    -------
    TransmissionLine
        A copied line with electrical and St. Clair results attached.
    """
    return calculate_line_electrical_parameters(line)


def calculate_electrical(
    geometry: TowerGeometry,
    *,
    phase_specs: list[PhaseConductorSpec],
    ground_wire_spec: GroundWireSpec,
    voltage: VoltageKV,
    frequency: Frequency,
    earth_resistivity: float,
) -> ElectricalParameters:
    """Calculate all Julia-parity electrical result matrices and scalars.

    Parameters
    ----------
    geometry : TowerGeometry
        Tower-local phase and ground-wire positions.
    phase_specs : list of PhaseConductorSpec
        One conductor/bundle specification per geometry circuit.
    ground_wire_spec : GroundWireSpec
        Shared ground-wire conductor properties.
    voltage : VoltageKV
        Nominal line-to-line system voltage.
    frequency : Frequency
        Power frequency.
    earth_resistivity : float
        Earth resistivity in ohm-meter.

    Returns
    -------
    ElectricalParameters
        Completed, JSON-safe primitive/reduced/transposed matrices and scalar
        sequence values, without an attached St. Clair curve.

    Raises
    ------
    ValueError
        If required physical cable values or positive-sequence SIL inputs are
        absent or invalid.
    """
    voltage = voltage.to("kilovolt")
    frequency = frequency.to("hertz")
    specs = {spec.circuit_id: spec for spec in phase_specs}
    positions, gmrs, radii, resistances, counts, labels, phase_count = _ordered_inputs(geometry, specs, ground_wire_spec)
    ground_count = len(geometry.ground_wire_positions)
    z_primitive = build_primitive_z(positions, gmrs=gmrs, resistances=resistances, bundle_counts=counts, frequency=frequency.magnitude, earth_resistivity=earth_resistivity)
    p_primitive = build_primitive_p(positions, radii=radii, frequency=frequency.magnitude)
    z_kron = kron_reduce(z_primitive, phase_count, ground_count)
    p_kron = kron_reduce(p_primitive, phase_count, ground_count)
    y_kron = shunt_admittance(p_kron, frequency.magnitude)
    z_sequence_nt = sequence_matrix(z_kron)
    y_sequence_nt = sequence_matrix(y_kron)
    circuits = phase_count // 3
    z_transposed = fully_transpose(z_kron, circuits)
    y_transposed = fully_transpose(y_kron, circuits)
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
    if b1 <= 0 or x1 <= 0:
        raise ValueError("positive sequence reactance and susceptance are required for SIL")
    z_sil = (x1 / (b1 / 1e6)) ** 0.5
    scalars = {"r1": float(r1), "x1": float(x1), "b1": float(b1), "r0": float(z_sequence[0, 0].real), "x0": float(z_sequence[0, 0].imag), "b0": float(y_sequence[0, 0].imag), "surge_impedance_ohm": float(z_sil), "sil_mw": float(voltage.magnitude**2 / z_sil)}
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
        spec.catalog_reference.model_dump()
        for spec in phase_specs
        if spec.catalog_reference is not None
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
        provenance=provenance,
        topology="one-circuit" if circuits == 1 else "two-circuit",
        status="complete",
        calculated_at=datetime.now(UTC),
    )


__all__ = ["EPSILON_AIR", "L_C", "L_F", "R_C", "build_primitive_p", "build_primitive_z", "calculate_electrical", "calculate_electrical_parameters", "calculate_line_electrical_parameters"]
