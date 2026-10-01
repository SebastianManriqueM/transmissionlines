"""Construct and optionally register cross-section input graphs."""

from transmissionlines.builders.system import assemble_line_into_system
from transmissionlines.models.assets import CrossSectionTransmissionLine
from transmissionlines.models.configurations import TowerConfiguration
from transmissionlines.system import TransmissionLineSystem
from transmissionlines.units import EarthResistivity, Frequency, VoltageKV


def cross_section_line(
    tower: TowerConfiguration, *, name: str, voltage_kv: float, frequency_hz: float,
    earth_resistivity_ohm_m: float, everyday_tension_fraction: float | None = None,
) -> CrossSectionTransmissionLine:
    """Create a standalone line with explicitly named engineering units."""
    return CrossSectionTransmissionLine(
        name=name, configuration=tower, nominal_voltage=VoltageKV(voltage_kv, "kilovolt"),
        nominal_frequency=Frequency(frequency_hz, "hertz"),
        earth_resistivity=EarthResistivity(earth_resistivity_ohm_m, "ohm * meter"),
        everyday_tension_fraction=everyday_tension_fraction,
    )


def system(*, name: str) -> TransmissionLineSystem:
    """Create an empty transmission-line input system."""
    return TransmissionLineSystem(name=name)


def add_line(
    system: TransmissionLineSystem, line: CrossSectionTransmissionLine,
) -> CrossSectionTransmissionLine:
    """Preflight and register a selected cross-section input graph."""
    return assemble_line_into_system(system, line)