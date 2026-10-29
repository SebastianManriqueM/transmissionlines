"""Pure NumPy matrix operations for the Julia-parity electrical engine."""

from math import pi

import numpy as np


def kron_reduce(matrix: np.ndarray, phase_count: int, ground_count: int) -> np.ndarray:
    r"""Eliminate the grounded conductors (the last ``ground_count``) by Kron reduction.

    With the matrix partitioned into phase (p) and ground (g) blocks, and ground
    wires at zero potential,

    .. math:: M_{\text{red}} = M_{pp} - M_{pg} M_{gg}^{-1} M_{gp}.
    """
    value = np.asarray(matrix, dtype=complex)
    pp = value[:phase_count, :phase_count]
    pg = value[:phase_count, phase_count:]
    gp = value[phase_count:, :phase_count]
    gg = value[phase_count:, phase_count:]
    return pp - pg @ np.linalg.solve(gg, gp)


def shunt_admittance(potential: np.ndarray, frequency: float) -> np.ndarray:
    r"""Shunt admittance from potential coefficients, in µS/mile.

    .. math:: Y = j \omega C = j\, 2\pi f\, P^{-1}

    with :math:`P` in mile/µF, so :math:`P^{-1}` is capacitance in µF/mile.
    """
    return 1j * 2 * pi * frequency * np.linalg.inv(potential)


def fully_transpose(matrix: np.ndarray) -> np.ndarray:
    r"""Apply full transposition to a 3N-conductor phase matrix (N circuits).

    A fully transposed line averages each phase over every position. Within each
    circuit's 3x3 block :math:`B`,

    .. math::
        z_s = \tfrac13 \textstyle\sum_i B_{ii}, \qquad
        z_m = \tfrac16 \textstyle\sum_{i \ne j} B_{ij},

    giving :math:`z_s` on the diagonal and :math:`z_m` elsewhere. Every block coupling
    two different circuits becomes its overall mean.
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
    r"""Transform a 3N phase matrix into symmetrical-component (0, 1, 2) coordinates.

    Per circuit, with :math:`a = e^{j 2\pi/3}`,

    .. math::
        Z_{012} = A^{-1} Z_{abc} A, \qquad
        A = \begin{bmatrix} 1 & 1 & 1 \\ 1 & a^2 & a \\ 1 & a & a^2 \end{bmatrix}.

    For a transposed block (:math:`z_s` on the diagonal, :math:`z_m` elsewhere) this
    is diagonal: :math:`z_0 = z_s + 2 z_m` and :math:`z_1 = z_2 = z_s - z_m`.
    """
    value = np.asarray(matrix, dtype=complex)
    a = np.exp(2j * pi / 3)
    transform = np.array([[1, 1, 1], [1, a**2, a], [1, a, a**2]], dtype=complex)
    inverse = np.linalg.inv(transform)
    blocks = value.shape[0] // 3
    t = np.kron(np.eye(blocks), transform)
    ti = np.kron(np.eye(blocks), inverse)
    return ti @ value @ t


__all__ = ["fully_transpose", "kron_reduce", "sequence_matrix", "shunt_admittance"]
