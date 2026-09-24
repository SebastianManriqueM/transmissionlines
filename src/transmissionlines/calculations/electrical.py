"""Pure Julia-parity electrical calculation orchestration."""

from datetime import UTC, datetime
from math import log, pi
import numpy as np

from transmissionlines.calculations.cable import ground_wire_gmr
from transmissionlines.calculations.geometry import direct_distance, image_distance
from transmissionlines.calculations.matrices import (
    fully_transpose,
    kron_reduce,
    sequence_matrix,
    shunt_admittance,
)
from transmissionlines.models.cables import GroundWireSpec, PhaseConductorSpec
from transmissionlines.models.electrical import ElectricalParameters
from transmissionlines.models.geometry import CablePosition, TowerGeometry
from transmissionlines.units import Frequency, VoltageKV

R_C = 0.00158836
L_C = 0.00202237
L_F = 7.6786
EPSILON_AIR = 1.4240e-2


def _complex_json(matrix: np.ndarray) -> list[list[dict[str, float]]]:
    return [[{"real": float(cell.real), "imag": float(cell.imag)} for cell in row] for row in matrix]


def build_primitive_z(
    positions: list[CablePosition],
    *,
    gmrs: list[float],
    resistances: list[float],
    bundle_counts: list[int],
    frequency: float,
    earth_resistivity: float,
) -> np.ndarray:
    """Build the primitive series impedance matrix in ohm/mile."""
    n = len(positions)
    if not (len(gmrs) == len(resistances) == len(bundle_counts) == n):
        raise ValueError("primitive Z inputs must have equal lengths")
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
    """Build the primitive potential matrix in the Julia micro-unit contract."""
    del frequency  # retained in the signature to make the unit boundary explicit
    if len(radii) != len(positions):
        raise ValueError("potential radii and positions must have equal lengths")
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


def calculate_electrical(
    geometry: TowerGeometry,
    *,
    phase_specs: list[PhaseConductorSpec],
    ground_wire_spec: GroundWireSpec,
    voltage: VoltageKV,
    frequency: Frequency,
    earth_resistivity: float,
) -> ElectricalParameters:
    """Calculate and serialize all Julia-parity electrical result matrices."""
    specs = {spec.circuit_id: spec for spec in phase_specs}
    positions, gmrs, radii, resistances, counts, labels, phase_count = _ordered_inputs(geometry, specs, ground_wire_spec)
    ground_count = len(geometry.ground_wire_positions)
    z_primitive = build_primitive_z(positions, gmrs=gmrs, resistances=resistances, bundle_counts=counts, frequency=frequency.magnitude, earth_resistivity=earth_resistivity)
    p_primitive = build_primitive_p(positions, radii=radii, frequency=frequency.magnitude)
    z_kron = kron_reduce(z_primitive, phase_count, ground_count)
    p_kron = kron_reduce(p_primitive, phase_count, ground_count)
    y_kron = shunt_admittance(p_kron, frequency.magnitude)
    circuits = phase_count // 3
    z_transposed = fully_transpose(z_kron, circuits)
    y_transposed = fully_transpose(y_kron, circuits)
    z_sequence = sequence_matrix(z_transposed)
    y_sequence = sequence_matrix(y_transposed)
    r1, x1 = z_sequence[1, 1].real, z_sequence[1, 1].imag
    b1 = y_sequence[1, 1].imag
    if b1 <= 0 or x1 <= 0:
        raise ValueError("positive sequence reactance and susceptance are required for SIL")
    z_sil = (x1 / (b1 / 1e6)) ** 0.5
    scalars = {"r1": float(r1), "x1": float(x1), "b1": float(b1), "r0": float(z_sequence[0, 0].real), "x0": float(z_sequence[0, 0].imag), "b0": float(y_sequence[0, 0].imag), "surge_impedance_ohm": float(z_sil), "sil_mw": float(voltage.magnitude**2 / z_sil)}
    if circuits == 2:
        scalars.update({"r0_mutual": float(z_sequence[3, 0].real), "x0_mutual": float(z_sequence[3, 0].imag), "b0_mutual": float(y_sequence[3, 0].imag)})
    matrices = {"Z_primitive": _complex_json(z_primitive), "P_primitive": _complex_json(p_primitive), "Z_kron": _complex_json(z_kron), "P_kron": _complex_json(p_kron), "Y_kron": _complex_json(y_kron), "Z_transposed": _complex_json(z_transposed), "Y_transposed": _complex_json(y_transposed), "Z_sequence": _complex_json(z_sequence), "Y_sequence": _complex_json(y_sequence)}
    return ElectricalParameters(labels=labels, matrices=matrices, scalars=scalars, calculated_at=datetime.now(UTC))


__all__ = ["EPSILON_AIR", "L_C", "L_F", "R_C", "build_primitive_p", "build_primitive_z", "calculate_electrical"]
