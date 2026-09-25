"""Canonical Infrasys transmission-line and dynamic-rating schemas."""

from enum import StrEnum
from typing import Annotated, Literal

from infrasys import Component, Location, SupplementalAttribute
from pydantic import AwareDatetime, Field
from r2x_core import HasUnits, Unit

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.electrical import ElectricalParameters


class TowerType(StrEnum):
    """Structural form of a transmission-line support."""

    LATTICE = "LATTICE"
    POLE = "POLE"
    H_FRAME = "H_FRAME"
    UNKNOWN = "UNKNOWN"


class ConductorMaterial(StrEnum):
    """Conductor construction family."""

    ACSR = "ACSR"
    AAC = "AAC"
    AAAC = "AAAC"
    ACAR = "ACAR"
    COPPER = "COPPER"
    OTHER = "OTHER"


class ParameterDomain(StrEnum):
    """Discipline represented by a conductor parameter set."""

    MECHANICAL = "MECHANICAL"
    ELECTRICAL = "ELECTRICAL"
    THERMAL = "THERMAL"


class WeatherVariable(StrEnum):
    """Name of a weather time series attached to a weather station."""

    AMBIENT_TEMPERATURE = "ambient_temperature"
    EASTWARD_WIND_VELOCITY = "eastward_wind_velocity"
    NORTHWARD_WIND_VELOCITY = "northward_wind_velocity"
    SOLAR_IRRADIANCE = "solar_irradiance"


Longitude = Annotated[float, Field(ge=-180, le=180), Unit("degree")]
Latitude = Annotated[float, Field(ge=-90, le=90), Unit("degree")]


class CatalogReference(LineDataModel):
    """Immutable pointer to source catalog data."""

    catalog_version: str
    table_name: str
    record_id: str
    source_id: str | None = None


class IdentificationInfo(LineDataModel):
    """Immutable source identification values."""

    geometry_id: str | None = None
    structure_code: str | None = None
    structure_type: str | None = None


class GeoJSONMultiLineString(LineDataModel):
    """Immutable GeoJSON route geometry."""

    type: Literal["MultiLineString"] = "MultiLineString"
    coordinates: list[list[tuple[Longitude, Latitude]]] = Field(min_length=1)


class GeographicLocation(HasUnits, Location):
    """UUID-identified WGS 84 location component."""

    name: str = ""
    x: Longitude
    y: Latitude
    crs: Literal["EPSG:4326"] = "EPSG:4326"


class GeographicPoint(LineDataModel):
    """Immutable geographic point value."""

    latitude: Latitude
    longitude: Longitude
    elevation: Annotated[float | None, Field(default=None, ge=0), Unit("m")] = None


class DLRComponent(HasUnits, Component):
    """Named unit-aware domain component."""

    name: str


class Bus(DLRComponent):
    """Named network terminal component."""

    location: GeographicPoint


class ConductorParameterSet(DLRComponent):
    """Reusable conductor parameter component."""

    domain: ParameterDomain


class MechanicalConductorParameters(ConductorParameterSet):
    """Reusable mechanical conductor parameters."""

    domain: Literal[ParameterDomain.MECHANICAL] = ParameterDomain.MECHANICAL
    diameter: Annotated[float, Field(gt=0), Unit("mm")]
    mass_per_length: Annotated[float, Field(gt=0), Unit("kg/m")]
    elastic_modulus: Annotated[float, Field(gt=0), Unit("GPa")]
    thermal_expansion_coefficient: Annotated[float, Field(ge=0), Unit("1/K")]
    rated_tensile_strength: Annotated[float, Field(gt=0), Unit("kN")]


class ElectricalConductorParameters(ConductorParameterSet):
    """Reusable electrical conductor parameters."""

    domain: Literal[ParameterDomain.ELECTRICAL] = ParameterDomain.ELECTRICAL
    ac_resistance_at_reference_temperature: Annotated[float, Field(gt=0), Unit("ohm/km")]
    reference_temperature: Annotated[float, Field(gt=-273.15), Unit("°C")]
    resistance_temperature_coefficient: Annotated[float, Unit("1/K")]


class ThermalConductorParameters(ConductorParameterSet):
    """Reusable thermal conductor parameters."""

    domain: Literal[ParameterDomain.THERMAL] = ParameterDomain.THERMAL
    heat_capacity_per_length: Annotated[float, Field(gt=0), Unit("J/(m*K)")]
    surface_emissivity: Annotated[float, Field(gt=0, le=1), Unit("dimensionless")]
    solar_absorptivity: Annotated[float, Field(gt=0, le=1), Unit("dimensionless")]


class BareConductorEquipment(LineDataModel):
    """Immutable conductor measurements used by electrical calculations."""

    material: ConductorMaterial = ConductorMaterial.OTHER
    conductor_diameter: Annotated[float | None, Field(gt=0), Unit("inch")] = None
    conductor_gmr: Annotated[float | None, Field(gt=0), Unit("ft")] = None
    capacitance_radius: Annotated[float | None, Field(gt=0), Unit("ft")] = None
    ac_resistance: Annotated[float | None, Field(gt=0), Unit("ohm/kft")] = None
    dc_resistance: Annotated[float | None, Field(gt=0), Unit("ohm/kft")] = None


class Conductor(DLRComponent):
    """Reusable conductor design component."""

    material: ConductorMaterial
    mechanical_parameters: MechanicalConductorParameters
    electrical_parameters: ElectricalConductorParameters
    thermal_parameters: ThermalConductorParameters


class CableSpec(DLRComponent):
    """Registered conductor selection component."""

    name: str = ""
    conductor: BareConductorEquipment
    catalog_reference: CatalogReference | None = None


class GroundWireSpec(CableSpec):
    """Registered ground-wire selection component."""


class PhaseConductorSpec(CableSpec):
    """Registered phase-conductor selection component."""

    circuit_id: str
    subconductor_count: Annotated[int, Field(gt=0)] = 1
    subconductor_spacing: Annotated[float | None, Field(gt=0), Unit("inch")] = None


class PhasePosition(LineDataModel):
    """Immutable tower-local phase position."""

    circuit_id: str
    phase: Literal["A", "B", "C"]
    x: Annotated[float, Unit("ft")]
    y: Annotated[float, Unit("ft")]


class GroundWirePosition(LineDataModel):
    """Immutable tower-local ground-wire position."""

    wire_id: str
    x: Annotated[float, Unit("ft")]
    y: Annotated[float, Unit("ft")]


class TowerGeometry(LineDataModel):
    """Immutable tower-local conductor geometry."""

    phase_positions: list[PhasePosition] = Field(min_length=3)
    ground_wire_positions: list[GroundWirePosition] = Field(min_length=1)


class TowerConfiguration(DLRComponent):
    """Reusable tower arrangement and conductor selections."""

    identification_info: IdentificationInfo
    circuit_count: Annotated[int, Field(gt=0)]
    phases_per_circuit: Annotated[int, Field(gt=0)] = 3
    subconductors_per_phase: Annotated[int, Field(gt=0)] = 1
    conductor: Conductor
    geometry: TowerGeometry
    ground_wire_spec: GroundWireSpec
    phase_conductor_specs: list[PhaseConductorSpec]


class SingleCircuit(TowerConfiguration):
    """Single-circuit tower arrangement."""

    circuit_count: Literal[1] = 1


class DoubleCircuit(TowerConfiguration):
    """Double-circuit tower arrangement."""

    circuit_count: Literal[2] = 2


class ElectricalTower(DLRComponent):
    """Physical support structure component."""

    name: str = ""
    tower_type: TowerType
    configuration: TowerConfiguration
    location: GeographicLocation
    height: Annotated[float, Field(gt=0), Unit("m")]


class StartEnd(DLRComponent):
    """Endpoint pair component for one physical span."""

    name: str = ""
    start: ElectricalTower
    end: ElectricalTower


class LineSpan(DLRComponent):
    """Physical span component with route geometry."""

    name: str = ""
    start_end: StartEnd
    geometry: GeoJSONMultiLineString
    conductor_override: Conductor | None = None


class LineParameters(LineDataModel):
    """Immutable calculated line-result aggregate."""

    electrical_parameters: ElectricalParameters | None = None
    mechanical_parameters: MechanicalConductorParameters | None = None


class TransmissionLine(DLRComponent):
    """Transmission asset composed of ordered spans."""

    nominal_voltage: Annotated[float, Field(gt=0), Unit("kV")]
    nominal_frequency: Annotated[float, Field(gt=0), Unit("Hz")] = 60.0
    earth_resistivity: Annotated[float, Field(gt=0), Unit("ohm*m")] = 100.0
    spans: list[LineSpan] = Field(min_length=1)
    line_parameters: LineParameters = Field(default_factory=LineParameters)


class WeatherStation(DLRComponent):
    """Geographic owner component for weather time series."""

    location: GeographicLocation


class ThermalRatingParameters(DLRComponent):
    """Reusable conductor-temperature operating limit component."""

    maximum_conductor_temperature: Annotated[float, Field(gt=-273.15), Unit("°C")]


class DynamicLineRatingRun(DLRComponent):
    """Registered dynamic line-rating calculation run component."""

    line: TransmissionLine
    weather_stations: list[WeatherStation] = Field(min_length=1)
    thermal_rating_parameters: ThermalRatingParameters
    calculated_at: AwareDatetime
    algorithm_name: str
    algorithm_version: str


class DynamicLineRatingResult(HasUnits, SupplementalAttribute):
    """Time-valid span current rating supplemental attribute."""

    valid_at: AwareDatetime
    current_rating: Annotated[float, Field(ge=0), Unit("A")]
