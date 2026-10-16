import numpy as np

from transmissionlines.calculations.matrices import fully_transpose, kron_reduce, sequence_matrix


def test_kron_and_sequence_dimensions() -> None:
    matrix = np.diag([1, 2, 3, 4]).astype(complex)
    reduced = kron_reduce(matrix, 3, 1)
    assert reduced.shape == (3, 3)
    transposed = fully_transpose(reduced)
    assert transposed.shape == (3, 3)
    assert sequence_matrix(transposed).shape == (3, 3)


