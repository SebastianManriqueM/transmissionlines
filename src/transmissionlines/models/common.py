"""Define common immutable value models for transmission-line results."""

import math
from typing import Self

import numpy as np
from pydantic import Field, model_validator

from transmissionlines.models.base import LineDataModel


class ComplexMatrix(LineDataModel):
    """Represent a JSON-safe complex matrix with explicit engineering labels."""

    rows: int = Field(gt=0)
    columns: int = Field(gt=0)
    unit: str = Field(min_length=1)
    row_labels: tuple[str, ...]
    column_labels: tuple[str, ...]
    real: tuple[tuple[float, ...], ...]
    imaginary: tuple[tuple[float, ...], ...]

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        """Validate matrix dimensions and label counts."""
        if len(self.row_labels) != self.rows:
            raise ValueError("row_labels length must equal rows")
        if len(self.column_labels) != self.columns:
            raise ValueError("column_labels length must equal columns")
        for values, field_name in (
            (self.real, "real"),
            (self.imaginary, "imaginary"),
        ):
            if len(values) != self.rows or any(
                len(row) != self.columns for row in values
            ):
                raise ValueError(
                    f"{field_name} must have shape ({self.rows}, {self.columns})"
                )
            if any(not math.isfinite(value) for row in values for value in row):
                raise ValueError(f"{field_name} values must be finite")
        return self

    def as_array(self) -> np.ndarray[tuple[int, int], np.dtype[np.complex128]]:
        """Return the complex matrix as a NumPy array."""
        return np.asarray(self.real, dtype=float) + 1j * np.asarray(
            self.imaginary, dtype=float
        )