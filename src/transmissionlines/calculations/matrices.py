"""Pure NumPy matrix operations for the Julia-parity electrical engine."""

from math import pi

import numpy as np


def kron_reduce(matrix: np.ndarray, phase_count: int, ground_count: int) -> np.ndarray:
    """Kron-reduce the final ``ground_count`` rows and columns."""
    value = np.asarray(matrix, dtype=complex)
    pp = value[:phase_count, :phase_count]
    pg = value[:phase_count, phase_count:]
    gp = value[phase_count:, :phase_count]
    gg = value[phase_count:, phase_count:]
    return pp - pg @ np.linalg.solve(gg, gp)


def shunt_admittance(potential: np.ndarray, frequency: float) -> np.ndarray:
    """Return ``j 2 pi f P^-1`` in microSiemens/mile."""
    return 1j * 2 * pi * frequency * np.linalg.inv(potential)


def fully_transpose(matrix: np.ndarray) -> np.ndarray:
    """Apply full transposition to a 3N-conductor phase matrix (N circuits).

    Within each circuit's 3x3 block, every diagonal entry becomes the block's mean
    self term and every off-diagonal entry its mean mutual term. Every block
    coupling two different circuits becomes its overall mean.
    """
    value = np.asarray(matrix, dtype=complex)
    circuits = value.shape[0] // 3
    blocks = value.reshape(circuits, 3, circuits, 3)
    self_mean = np.einsum("aiai->a", blocks) / 3
    mutual_mean = (np.einsum("aiaj->a", blocks) - 3 * self_mean) / 6
    eye, ones, own_block = np.eye(3), np.ones((3, 3)), np.kron(np.eye(circuits), np.ones((3, 3)))
    within = np.kron(np.diag(self_mean), eye) + np.kron(np.diag(mutual_mean), ones - eye)
    between = np.kron(blocks.mean(axis=(1, 3)), ones)
    return np.where(own_block == 1, within, between)


def sequence_matrix(matrix: np.ndarray) -> np.ndarray:
    """Transform a 3N phase matrix into symmetrical-component coordinates."""
    value = np.asarray(matrix, dtype=complex)
    a = np.exp(2j * pi / 3)
    transform = np.array([[1, 1, 1], [1, a**2, a], [1, a, a**2]], dtype=complex)
    inverse = np.linalg.inv(transform)
    blocks = value.shape[0] // 3
    t = np.kron(np.eye(blocks), transform)
    ti = np.kron(np.eye(blocks), inverse)
    return ti @ value @ t


__all__ = ["fully_transpose", "kron_reduce", "sequence_matrix", "shunt_admittance"]
