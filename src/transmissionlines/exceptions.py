"""Package-specific exception types."""


class TransmissionLinesError(Exception):
    """Base exception for transmission-line package errors."""


class CalculationInputError(TransmissionLinesError, ValueError):
    """Raised when typed line inputs cannot support a calculation."""
