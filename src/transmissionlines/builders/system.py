"""Infrasys assembly helpers for canonical components."""

from transmissionlines.models import TransmissionLine
from transmissionlines.system import TransmissionLineSystem


def build_transmission_line(request: TransmissionLine) -> TransmissionLine:
    """Return a canonical transmission-line component without mutation."""
    return request


def assemble_line_into_system(
    system: TransmissionLineSystem,
    line: TransmissionLine,
) -> TransmissionLine:
    """Register a canonical line and its composed components in a system."""
    system.add_component(line)
    return line


__all__ = ["assemble_line_into_system", "build_transmission_line"]
