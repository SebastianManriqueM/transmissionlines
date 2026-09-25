"""Public behavior for the canonical Infrasys transmission-line schemas."""

from datetime import UTC, datetime, timedelta
from typing import get_args, get_origin

import pytest
from infrasys import Component, SingleTimeSeries, SupplementalAttribute, System
from pydantic import ValidationError
from r2x_core.units import UnitSpec, ureg

from transmissionlines.models import (
    Conductor,
    ConductorMaterial,
    DoubleCircuit,
    DynamicLineRatingResult,
    DynamicLineRatingRun,
    ElectricalConductorParameters,
    ElectricalTower,
    GeoJSONMultiLineString,
    GeographicLocation,
    GroundWireSpec,
    LineSpan,
    MechanicalConductorParameters,
    PhaseConductorSpec,
    PhasePosition,
    StartEnd,
    ThermalConductorParameters,
    ThermalRatingParameters,
    TowerGeometry,
    TowerType,
    TransmissionLine,
    WeatherStation,
    WeatherVariable,
)


def conductor(name: str = "acsr") -> Conductor:
    """Build one canonical registered conductor graph."""
    return Conductor(
        name=name,
        material=ConductorMaterial.ACSR,
        mechanical_parameters=MechanicalConductorParameters(
            name=f"{name}-mechanical",
            diameter=28.14,
            mass_per_length=1.627,
            elastic_modulus=68.9,
            thermal_expansion_coefficient=1.9e-5,
            rated_tensile_strength=137.0,
        ),
        electrical_parameters=ElectricalConductorParameters(
            name=f"{name}-electrical",
            ac_resistance_at_reference_temperature=0.073,
            reference_temperature=25.0,
            resistance_temperature_coefficient=0.004,
        ),
        thermal_parameters=ThermalConductorParameters(
            name=f"{name}-thermal",
            heat_capacity_per_length=1150.0,
            surface_emissivity=0.5,
            solar_absorptivity=0.5,
        ),
    )


def network() -> tuple[TransmissionLine, DynamicLineRatingRun, WeatherStation, LineSpan]:
    """Build a connected canonical component graph."""
    wire_conductor = conductor("ground-conductor")
    phase_conductor = conductor("phase-conductor")
    geometry = TowerGeometry(
        phase_positions=[
            PhasePosition(circuit_id="circuit-1", phase=phase, x=index * 4.0, y=30.0)
            for index, phase in enumerate(("A", "B", "C"))
        ],
        ground_wire_positions=[
            {"wire_id": "ground-1", "x": 4.0, "y": 40.0}
        ],
    )
    configuration = DoubleCircuit(
        name="double-circuit",
        identification_info={"structure_code": "example"},
        phases_per_circuit=3,
        subconductors_per_phase=2,
        conductor=phase_conductor,
        geometry=geometry,
        ground_wire_spec=GroundWireSpec(
            name="ground-wire",
            conductor=wire_conductor.model_dump().get("equipment", {}),
        ),
        phase_conductor_specs=[
            PhaseConductorSpec(
                name="circuit-1-phase",
                circuit_id="circuit-1",
                conductor=phase_conductor.model_dump().get("equipment", {}),
                subconductor_count=2,
                subconductor_spacing=18.0,
            )
        ],
    )
    start = ElectricalTower(
        name="tower-1",
        tower_type=TowerType.LATTICE,
        configuration=configuration,
        location=GeographicLocation(x=-117.3, y=34.5),
        height=35.0,
    )
    end = ElectricalTower(
        name="tower-2",
        tower_type=TowerType.LATTICE,
        configuration=configuration,
        location=GeographicLocation(x=-117.2, y=34.6),
        height=35.0,
    )
    span = LineSpan(
        name="span-1",
        start_end=StartEnd(name="endpoints-1", start=start, end=end),
        geometry=GeoJSONMultiLineString(
            coordinates=[
                [(-117.3, 34.5), (-117.25, 34.55)],
                [(-117.25, 34.55), (-117.2, 34.6)],
            ]
        ),
    )
    line = TransmissionLine(name="line-1", nominal_voltage=500.0, spans=[span])
    station = WeatherStation(
        name="station-1", location=GeographicLocation(x=-117.25, y=34.55)
    )
    run = DynamicLineRatingRun(
        name="run-1",
        line=line,
        weather_stations=[station],
        thermal_rating_parameters=ThermalRatingParameters(
            name="thermal-limit", maximum_conductor_temperature=100.0
        ),
        calculated_at=datetime(2025, 6, 1, 12, 5, tzinfo=UTC),
        algorithm_name="steady-state-heat-balance",
        algorithm_version="1.0.0",
    )
    return line, run, station, span


def test_domain_entities_are_infrasys_components_and_results_are_attributes() -> None:
    line, run, station, span = network()
    assert isinstance(line, Component)
    assert isinstance(run, Component)
    assert isinstance(station, Component)
    assert isinstance(span, Component)
    assert issubclass(DynamicLineRatingResult, SupplementalAttribute)


def test_component_graph_and_supplemental_result_round_trip(tmp_path) -> None:
    line, run, station, span = network()
    result = DynamicLineRatingResult(
        valid_at=datetime(2025, 6, 1, 12, tzinfo=UTC), current_rating=1200.0
    )
    system = System(auto_add_composed_components=True)
    system.add_component(run)
    for owner in (run, span, station):
        system.add_supplemental_attribute(owner, result)
    series = SingleTimeSeries(
        name=WeatherVariable.AMBIENT_TEMPERATURE.value,
        data=ureg.Quantity([30.0, 31.0], "°C"),
        resolution=timedelta(minutes=5),
        initial_timestamp=datetime(2025, 6, 1, 12, tzinfo=UTC),
    )
    system.add_time_series(series, station)
    path = tmp_path / "system.json"
    system.to_json(path, overwrite=True)
    restored = System.from_json(path)
    restored_span = restored.get_component_by_uuid(span.uuid)
    assert restored_span.uuid == span.uuid
    assert restored.get_supplemental_attributes_with_component(
        restored_span, DynamicLineRatingResult
    )[0].current_rating == 1200.0
    assert str(restored.get_time_series(station, WeatherVariable.AMBIENT_TEMPERATURE.value).data.units) == "degree_Celsius"
    system.close()
    restored.close()


def test_embedded_values_use_line_data_model_and_reject_invalid_geometry() -> None:
    geometry = GeoJSONMultiLineString(
        coordinates=[[(-117.3, 34.5), (-117.2, 34.6)]]
    )
    assert geometry.type == "MultiLineString"
    with pytest.raises(ValidationError):
        GeoJSONMultiLineString.model_validate(
            {"type": "LineString", "coordinates": [[-117.0, 34.0], [-116.0, 35.0]]}
        )


def test_unit_annotations_are_present_on_canonical_fields() -> None:
    expected = {
        MechanicalConductorParameters: {"diameter": "mm", "mass_per_length": "kg/m"},
        ElectricalTower: {"height": "m"},
        GeographicLocation: {"x": "degree", "y": "degree"},
        TransmissionLine: {"nominal_voltage": "kV"},
        ThermalRatingParameters: {"maximum_conductor_temperature": "°C"},
        DynamicLineRatingResult: {"current_rating": "A"},
    }
    for model_type, fields in expected.items():
        for field_name, unit in fields.items():
            metadata = model_type.model_fields[field_name].metadata
            assert unit in [item.unit for item in metadata if isinstance(item, UnitSpec)]


def test_nullable_schema_fields_are_explicit() -> None:
    field = LineSpan.model_fields["conductor_override"]
    annotation = field.annotation
    if get_origin(annotation) is not None:
        annotation = get_args(annotation)[0]
    assert type(None) in get_args(field.annotation)
    assert annotation is Conductor
