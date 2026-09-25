from __future__ import annotations

import pytest

from transmissionlines.calculations.electrical import calculate_line_electrical_parameters
from transmissionlines.api import calculate_st_clair_curve
from transmissionlines.models.assets import LineTechnicalInfo, TransmissionLine
from transmissionlines.models.cables import BareConductorEquipment, GroundWireSpec, PhaseConductorSpec
from transmissionlines.models.common import Bus, GeographicPoint
from transmissionlines.models.configurations import TowerConfiguration
from transmissionlines.models.electrical import ElectricalParameters
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.models.mechanical import MechanicalParameters
from transmissionlines.models.parameters import LineParameters
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.units import (
    Angle,
    CableDiameter,
    CableGMR,
    Current,
    EarthResistivity,
    Frequency,
    ResistancePerKft,
    TowerCoordinate,
    VoltageKV,
)


def _conductor() -> BareConductorEquipment:
    return BareConductorEquipment(
        conductor_diameter=CableDiameter(1, "inch"),
        conductor_gmr=CableGMR(0.04, "foot"),
        ampacity=Current(1000, "ampere"),
        ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot"),
        dc_resistance=ResistancePerKft(0.2, "ohm / kilofoot"),
    )


def _geometry() -> TowerGeometry:
    return TowerGeometry(
        phase_positions=[
            PhasePosition(circuit_id="c1", phase=phase, x=TowerCoordinate(index * 4, "foot"), y=TowerCoordinate(30, "foot"))
            for index, phase in enumerate(("A", "B", "C"))
        ],
        ground_wire_positions=[GroundWirePosition(wire_id="g1", x=TowerCoordinate(0, "foot"), y=TowerCoordinate(40, "foot"))],
    )


def _line(*, mechanical: MechanicalParameters | None = None) -> TransmissionLine:
    phase = PhaseConductorSpec(conductor=_conductor(), circuit_id="c1")
    ground = GroundWireSpec(conductor=_conductor())
    config = TowerConfiguration(name="config", identification_info={}, geometry=_geometry(), ground_wire_spec=ground, phase_conductor_specs=[phase])
    point_a = GeographicPoint(latitude=Angle(0, "degree"), longitude=Angle(0, "degree"))
    point_b = GeographicPoint(latitude=Angle(1, "degree"), longitude=Angle(1, "degree"))
    bus_a = Bus(name="from", location=point_a)
    bus_b = Bus(name="to", location=point_b)
    technical = LineTechnicalInfo(line_name="line", nominal_voltage=VoltageKV(230, "kilovolt"), nominal_frequency=Frequency(60, "hertz"), earth_resistivity=EarthResistivity(100, "ohm * meter"), from_bus=bus_a, to_bus=bus_b)
    parameters = None if mechanical is None else LineParameters(mechanical_parameters=mechanical)
    return TransmissionLine(name="line", technical_info=technical, tower_configuration=config, line_parameters=parameters)


def test_two_circuit_orchestration_dimensions_labels_and_mutual_scalars() -> None:
    line = _line()
    phases = [
        *line.tower_configuration.geometry.phase_positions,
        PhasePosition(circuit_id="c2", phase="A", x=TowerCoordinate(20, "foot"), y=TowerCoordinate(30, "foot")),
        PhasePosition(circuit_id="c2", phase="B", x=TowerCoordinate(24, "foot"), y=TowerCoordinate(30, "foot")),
        PhasePosition(circuit_id="c2", phase="C", x=TowerCoordinate(28, "foot"), y=TowerCoordinate(30, "foot")),
    ]
    grounds = [
        *line.tower_configuration.geometry.ground_wire_positions,
        GroundWirePosition(wire_id="g2", x=TowerCoordinate(10, "foot"), y=TowerCoordinate(40, "foot")),
    ]
    geometry = TowerGeometry(phase_positions=phases, ground_wire_positions=grounds)
    second_conductor = _conductor().model_copy(update={"ampacity": Current(1500, "ampere")})
    phase_specs = [
        *line.tower_configuration.phase_conductor_specs,
        PhaseConductorSpec(conductor=second_conductor, circuit_id="c2"),
    ]
    config = line.tower_configuration.model_copy(update={"geometry": geometry, "phase_conductor_specs": phase_specs})
    result = calculate_line_electrical_parameters(line.model_copy(update={"tower_configuration": config})).line_parameters.electrical_parameters
    assert result is not None
    assert result.matrices["Zabcg"].row_count == 8
    assert result.matrices["Z_kron"].row_count == 6
    assert result.matrices["Z012_ft"].row_labels == ["1:zero", "1:positive", "1:negative", "2:zero", "2:positive", "2:negative"]
    assert result.matrices["Z_kron"] is result.matrices["Z_kron_nt"]
    assert "r0_mutual" in result.scalars
    assert set(result.circuit_scalars) == {"c1", "c2"}
    assert result.st_clair_curve is not None
    assert [curve.circuit_id for curve in result.st_clair_curve.curves] == ["c1", "c2"]
    assert result.circuit_scalars["c1"] != result.circuit_scalars["c2"]
    assert result.st_clair_curve.line_constants[0].r_ohm_per_mile == pytest.approx(
        result.circuit_scalars["c1"]["r1"]
    )
    assert [curve.circuit_nominal_ampacity_a for curve in result.st_clair_curve.curves] == [1000, 1500]
    assert result.st_clair_curve.curves[0].thermal_power_mw != result.st_clair_curve.curves[1].thermal_power_mw


def test_high_level_calculation_does_not_need_routing_and_preserves_mechanical() -> None:
    mechanical = MechanicalParameters(method="fixture", version="1")
    original = _line(mechanical=mechanical)
    calculated = calculate_line_electrical_parameters(original)
    assert original.routing_info is None
    assert original.line_parameters is not None
    assert original.line_parameters.electrical_parameters is None
    assert calculated.line_parameters is not None
    assert calculated.line_parameters.electrical_parameters is not None
    assert calculated.line_parameters.electrical_parameters.st_clair_curve is not None
    assert original.line_parameters.electrical_parameters is None
    assert calculated.line_parameters.mechanical_parameters == mechanical
    assert calculated is not original
    repeated = calculate_line_electrical_parameters(original)
    assert repeated.line_parameters is not calculated.line_parameters
    restored = ElectricalParameters.model_validate_json(calculated.line_parameters.electrical_parameters.model_dump_json())
    assert restored.matrices["Zabcg"].unit == "ohm/mile"


def test_explicit_curve_recalculation_is_immutable_and_keeps_sensitivities() -> None:
    original = _line()
    calculated = calculate_line_electrical_parameters(original)
    updated = calculate_st_clair_curve(
        calculated,
        options=StClairOptions(line_length_start_mi=20, line_length_stop_mi=20),
        sensitivities={"n_series_percent": [0, 10]},
    )
    assert original.line_parameters is None
    assert calculated.line_parameters.electrical_parameters.st_clair_curve.sensitivity_curves == []
    result = updated.line_parameters.electrical_parameters.st_clair_curve
    assert len(result.sensitivity_curves) == 2
    assert result.curves[0].circuit_id == "c1"


def test_completed_result_rejects_missing_canonical_matrix() -> None:
    result = calculate_line_electrical_parameters(_line()).line_parameters.electrical_parameters
    assert result is not None
    data = result.model_dump()
    data["matrices"].pop("Y012_nt")
    with pytest.raises(ValueError, match="missing matrices"):
        ElectricalParameters.model_validate(data)


def test_high_level_calculation_normalizes_compatible_technical_units() -> None:
    original = _line()
    technical = original.technical_info.model_copy(
        update={
            "nominal_voltage": VoltageKV(230000, "volt"),
            "nominal_frequency": Frequency(0.06, "kilohertz"),
            "earth_resistivity": EarthResistivity(10000, "ohm * centimeter"),
        }
    )
    alternate = calculate_line_electrical_parameters(original.model_copy(update={"technical_info": technical}))
    baseline = calculate_line_electrical_parameters(original)
    assert alternate.line_parameters.electrical_parameters.scalars == pytest.approx(
        baseline.line_parameters.electrical_parameters.scalars
    )


def test_high_level_calculation_reports_missing_conductor_fields() -> None:
    line = _line()
    phase = line.tower_configuration.phase_conductor_specs[0]
    incomplete = phase.model_copy(update={"conductor": BareConductorEquipment(ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot"))})
    config = line.tower_configuration.model_copy(update={"phase_conductor_specs": [incomplete]})
    with pytest.raises(ValueError, match="missing required conductor"):
        calculate_line_electrical_parameters(line.model_copy(update={"tower_configuration": config}))


def test_high_level_calculation_reports_circuit_mapping_errors() -> None:
    original = _line()
    bad_config = original.tower_configuration.model_copy(update={"phase_conductor_specs": []})
    bad_line = original.model_copy(update={"tower_configuration": bad_config})
    with pytest.raises(ValueError, match=r"missing=\['c1'\]"):
        calculate_line_electrical_parameters(bad_line)
