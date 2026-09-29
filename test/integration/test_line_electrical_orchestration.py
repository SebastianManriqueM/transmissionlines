from __future__ import annotations

import pytest

from transmissionlines.api import calculate_st_clair_curve
from transmissionlines.calculations.electrical import calculate_line_electrical_parameters
from transmissionlines.models.assets import CrossSectionTransmissionLine
from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec, GroundWireSpec, InsulatorStringSpec
from transmissionlines.models.common import IdentificationInfo
from transmissionlines.models.configurations import CircuitConfiguration, TowerConfiguration
from transmissionlines.models.electrical import ElectricalParameters
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.models.st_clair import StClairOptions
from test.integration.test_calculation_input_graph import _routed_line
from transmissionlines.units import (
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


def _circuit(circuit_id: str, conductor: BareConductorEquipment) -> CircuitConfiguration:
    return CircuitConfiguration(
        name=circuit_id, circuit_id=circuit_id,
        conductor_spec=ConductorSpec(name=f"conductor:{circuit_id}", equipment=conductor),
        bundle_spec=BundleSpec(subconductor_count=1),
        insulator_string=InsulatorStringSpec(
            insulator_type="glass", number_of_insulators=12,
            insulator_code="U120B", insulator_coupling="ball_and_socket",
        ),
    )


def _line(configuration: TowerConfiguration | None = None) -> CrossSectionTransmissionLine:
    configuration = configuration or TowerConfiguration(
        name="config", identification_info=IdentificationInfo(), geometry=_geometry(),
        ground_wire_spec=GroundWireSpec(name="ground", equipment=_conductor()),
        circuits=[_circuit("c1", _conductor())],
    )
    return CrossSectionTransmissionLine(
        name="line", configuration=configuration,
        nominal_voltage=VoltageKV(230, "kilovolt"), nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )


@pytest.mark.parametrize("kind", ["cross-section", "routed"])
def test_two_circuit_orchestration_dimensions_labels_and_mutual_scalars(kind: str) -> None:
    line = _line()
    phases = [
        *line.configuration.geometry.phase_positions,
        PhasePosition(circuit_id="c2", phase="A", x=TowerCoordinate(20, "foot"), y=TowerCoordinate(30, "foot")),
        PhasePosition(circuit_id="c2", phase="B", x=TowerCoordinate(24, "foot"), y=TowerCoordinate(30, "foot")),
        PhasePosition(circuit_id="c2", phase="C", x=TowerCoordinate(28, "foot"), y=TowerCoordinate(30, "foot")),
    ]
    grounds = [
        *line.configuration.geometry.ground_wire_positions,
        GroundWirePosition(wire_id="g2", x=TowerCoordinate(10, "foot"), y=TowerCoordinate(40, "foot")),
    ]
    geometry = TowerGeometry(phase_positions=phases, ground_wire_positions=grounds)
    second_conductor = _conductor().model_copy(update={"ampacity": Current(1500, "ampere")})
    phase_specs = [
        *line.configuration.circuits,
        _circuit("c2", second_conductor),
    ]
    config = line.configuration.model_copy(update={"geometry": geometry, "circuits": phase_specs})
    selected = _line(config) if kind == "cross-section" else _routed_line(configuration=config)[0]
    calculated = calculate_line_electrical_parameters(selected)
    result = calculated.electrical
    assert result is not None
    assert result.matrices["Zabcg"].row_count == 8
    assert result.matrices["Z_kron"].row_count == 6
    assert result.matrices["Z012_ft"].row_labels == ["1:zero", "1:positive", "1:negative", "2:zero", "2:positive", "2:negative"]
    assert result.matrices["Z_kron"] is result.matrices["Z_kron_nt"]
    assert "r0_mutual" in result.scalars
    assert set(result.circuit_scalars) == {"c1", "c2"}
    assert calculated.st_clair is not None
    assert [curve.circuit_id for curve in calculated.st_clair.curves] == ["c1", "c2"]
    assert result.circuit_scalars["c1"] != result.circuit_scalars["c2"]
    assert calculated.st_clair.line_constants[0].r_ohm_per_mile == pytest.approx(
        result.circuit_scalars["c1"]["r1"]
    )
    assert [curve.circuit_nominal_ampacity_a for curve in calculated.st_clair.curves] == [1000, 1500]
    assert calculated.st_clair.curves[0].thermal_power_mw != calculated.st_clair.curves[1].thermal_power_mw


def test_high_level_calculation_does_not_need_routing_and_preserves_inputs() -> None:
    original = _line()
    calculated = calculate_line_electrical_parameters(original)
    assert "spans" not in type(original).model_fields
    assert "line_parameters" not in type(original).model_fields
    assert calculated.electrical is not None
    assert calculated.st_clair is not None
    assert "mechanical_parameters" not in type(calculated).model_fields
    assert calculated is not original
    repeated = calculate_line_electrical_parameters(original)
    assert repeated.electrical is not calculated.electrical
    restored = ElectricalParameters.model_validate_json(calculated.electrical.model_dump_json())
    assert restored.matrices["Zabcg"].unit == "ohm/mile"


def test_explicit_curve_recalculation_is_immutable_and_keeps_sensitivities() -> None:
    original = _line()
    calculated = calculate_line_electrical_parameters(original)
    updated = calculate_st_clair_curve(
        original,
        previous=calculated,
        options=StClairOptions(line_length_start_mi=20, line_length_stop_mi=20),
        sensitivities={"n_series_percent": [0, 10]},
    )
    assert "line_parameters" not in type(original).model_fields
    assert calculated.st_clair.sensitivity_curves == []
    result = updated
    assert len(result.sensitivity_curves) == 2
    assert result.curves[0].circuit_id == "c1"


def test_completed_result_rejects_missing_canonical_matrix() -> None:
    result = calculate_line_electrical_parameters(_line()).electrical
    assert result is not None
    data = result.model_dump()
    data["matrices"].pop("Y012_nt")
    with pytest.raises(ValueError, match="missing matrices"):
        ElectricalParameters.model_validate(data)


def test_high_level_calculation_normalizes_compatible_technical_units() -> None:
    original = _line()
    alternate = calculate_line_electrical_parameters(original.model_copy(update={
        "nominal_voltage": VoltageKV(230000, "volt"),
        "nominal_frequency": Frequency(0.06, "kilohertz"),
        "earth_resistivity": EarthResistivity(10000, "ohm * centimeter"),
    }))
    baseline = calculate_line_electrical_parameters(original)
    assert alternate.electrical.scalars == pytest.approx(
        baseline.electrical.scalars
    )


def test_high_level_calculation_reports_missing_conductor_fields() -> None:
    line = _line()
    phase = line.configuration.circuits[0]
    incomplete = phase.model_copy(update={"conductor_spec": ConductorSpec(name="incomplete", equipment=BareConductorEquipment(ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot")))})
    config = line.configuration.model_copy(update={"circuits": [incomplete]})
    with pytest.raises(ValueError, match="missing required conductor"):
        calculate_line_electrical_parameters(_line(config))


def test_high_level_calculation_reports_circuit_mapping_errors() -> None:
    original = _line()
    bad_config = original.configuration.model_copy(update={"circuits": []})
    bad_line = original.model_copy(update={"configuration": bad_config})
    with pytest.raises(ValueError, match=r"missing=\['c1'\]"):
        calculate_line_electrical_parameters(bad_line)
