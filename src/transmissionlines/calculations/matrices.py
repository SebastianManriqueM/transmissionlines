"""Pure NumPy matrix operations for the Julia-parity electrical engine."""

from math import pi

import numpy as np


def _square(matrix: np.ndarray, name: str) -> np.ndarray:
    value = np.asarray(matrix, dtype=complex)
    if value.ndim != 2 or value.shape[0] != value.shape[1]:
        raise ValueError(f"{name} must be square")
    return value


def kron_reduce(matrix: np.ndarray, phase_count: int, ground_count: int) -> np.ndarray:
    """Kron-reduce the final ``ground_count`` rows and columns."""
    value = _square(matrix, "matrix")
    if phase_count <= 0 or ground_count <= 0 or value.shape != (phase_count + ground_count,) * 2:
        raise ValueError("matrix dimensions do not match phase and ground partitions")
    pp = value[:phase_count, :phase_count]
    pg = value[:phase_count, phase_count:]
    gp = value[phase_count:, :phase_count]
    gg = value[phase_count:, phase_count:]
    return pp - pg @ np.linalg.solve(gg, gp)


def shunt_admittance(potential: np.ndarray, frequency: float) -> np.ndarray:
    """Return ``j 2 pi f P^-1`` in microSiemens/mile."""
    if frequency <= 0:
        raise ValueError("frequency must be positive")
    return 1j * 2 * pi * frequency * np.linalg.inv(_square(potential, "potential"))


def fully_transpose(matrix: np.ndarray, circuit_count: int | None = None) -> np.ndarray:
    """Apply full transposition to a 3- or 3N-conductor phase matrix."""
    value = _square(matrix, "matrix")
    if circuit_count is None:
        if value.shape[0] % 3:
            raise ValueError("phase matrix must have a multiple of three rows")
        circuit_count = value.shape[0] // 3
    if circuit_count < 1 or value.shape != (3 * circuit_count,) * 2:
        raise ValueError("matrix dimensions do not match circuit count")
    result = np.zeros_like(value)
    for c in range(circuit_count):
        block = value[3 * c : 3 * c + 3, 3 * c : 3 * c + 3]
        diagonal = np.mean(np.diag(block))
        off_diagonal = (np.sum(block) - np.trace(block)) / 6
        result[3 * c : 3 * c + 3, 3 * c : 3 * c + 3] = (
            np.eye(3, dtype=complex) * diagonal
            + (np.ones((3, 3), dtype=complex) - np.eye(3)) * off_diagonal
        )
    for left in range(circuit_count):
        for right in range(circuit_count):
            if left == right:
                continue
            block = value[3 * left : 3 * left + 3, 3 * right : 3 * right + 3]
            result[3 * left : 3 * left + 3, 3 * right : 3 * right + 3] = np.mean(block)
    return result


def sequence_matrix(matrix: np.ndarray) -> np.ndarray:
    """Transform a 3N phase matrix into symmetrical-component coordinates."""
    value = _square(matrix, "matrix")
    if value.shape[0] % 3:
        raise ValueError("matrix dimension must be a multiple of three")
    a = np.exp(2j * pi / 3)
    transform = np.array([[1, 1, 1], [1, a**2, a], [1, a, a**2]], dtype=complex)
    inverse = np.linalg.inv(transform)
    blocks = value.shape[0] // 3
    t = np.kron(np.eye(blocks), transform)
    ti = np.kron(np.eye(blocks), inverse)
    return ti @ value @ t


__all__ = ["fully_transpose", "kron_reduce", "sequence_matrix", "shunt_admittance"]
