import pytest

from transmissionlines.calculations.electrical import calculate_line_electrical_parameters, calculate_st_clair_curve_for_line
from transmissionlines.models.assets import CrossSectionTransmissionLine, RoutedTransmissionLine
from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec, GroundWireSpec, InsulatorStringSpec
from transmissionlines.models.common import Bus, GeographicPoint, IdentificationInfo
from transmissionlines.models.configurations import CircuitConfiguration, TowerConfiguration
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.models.routing import ElectricalTower, LineSpan, RouteGeometry, StartEnd


def _configuration() -> TowerConfiguration:
    equipment = BareConductorEquipment(
        diameter_in=1,
        gmr_ft=0.04,
        ampacity_a=1000,
        ac_resistance_ohm_kft=0.1,
        dc_resistance_ohm_kft=0.2,
    )
    return TowerConfiguration(
        name="configuration", identification_info=IdentificationInfo(),
        geometry=TowerGeometry(
            phase_positions=[
                PhasePosition(circuit_id="c1", phase=phase, x_ft=index * 4, y_ft=30)
                for index, phase in enumerate(("A", "B", "C"))
            ],
            ground_wire_positions=[GroundWirePosition(wire_id="g1", x_ft=0, y_ft=40)],
        ),
        circuits=[CircuitConfiguration(
            name="c1", circuit_id="c1", conductor_spec=ConductorSpec(name="conductor", equipment=equipment),
            bundle_spec=BundleSpec(subconductor_count=1),
            insulator_string=InsulatorStringSpec(
                insulator_type="glass", number_of_insulators=12,
                insulator_code="U120B", insulator_coupling="ball_and_socket",
            ),
        )],
        ground_wire_spec=GroundWireSpec(name="ground", equipment=equipment),
    )


def test_cross_section_returns_external_results_without_mutating_inputs() -> None:
    line = CrossSectionTransmissionLine(
        name="line", configuration=_configuration(),
        nominal_voltage_kv=230,
        nominal_frequency_hz=60,
        earth_resistivity_ohm_m=100,
    )
    result = calculate_line_electrical_parameters(line)
    assert result.line_name == line.name
    assert result.electrical.status == "complete"
    assert result.st_clair is not None
    assert result.st_clair.curves[0].circuit_id == "c1"
    assert "line_parameters" not in type(line).model_fields
    _, foreign, _ = _routed_line()
    with pytest.raises(ValueError, match="does not accept a tower"):
        calculate_line_electrical_parameters(line, tower=foreign)


def _routed_line(*, different: bool = False, configuration: TowerConfiguration | None = None) -> tuple[RoutedTransmissionLine, ElectricalTower, ElectricalTower]:
    configuration = configuration or _configuration()
    end_configuration = _configuration().model_copy(update={"name": "second"}) if different else configuration
    locations = [
        GeographicPoint(latitude_deg=45, longitude_deg=longitude)
        for longitude in (-108, -107)
    ]
    start, end = [
        ElectricalTower(
            name=f"tower:{index}", tower_id=f"T{index}", sequence=index,
            location=locations[index], configuration=selected,
            structure_form="pole", support_role="terminal",
        )
        for index, selected in enumerate((configuration, end_configuration))
    ]
    span = LineSpan(
        name="span:0", span_id="S0", sequence=0,
        start_end=StartEnd(name="ends:0", start=start, end=end),
        route_geometry=RouteGeometry(coordinates=[(-108, 45), (-107, 45)]),
    )
    line = RoutedTransmissionLine(
        name="routed", from_bus=Bus(name="from", location=locations[0]),
        to_bus=Bus(name="to", location=locations[1]), spans=[span],
        nominal_voltage_kv=230, nominal_frequency_hz=60,
        earth_resistivity_ohm_m=100,
    )
    return line, start, end


def test_routed_shared_configuration_returns_selected_cross_section() -> None:
    line, start, _ = _routed_line()
    result = calculate_line_electrical_parameters(line)
    assert result.st_clair.line_name == line.name
    assert result.electrical.status == "complete"
    assert result.st_clair is not None
    assert "line_parameters" not in type(line).model_fields


def test_routed_heterogeneous_requires_an_owned_tower() -> None:
    line, start, end = _routed_line(different=True)
    with pytest.raises(ValueError, match="select a tower"):
        calculate_line_electrical_parameters(line)
    result = calculate_line_electrical_parameters(line, tower=end)
    assert result.electrical.status == "complete"
    assert calculate_st_clair_curve_for_line(line, tower=end).line_name == line.name
    assert calculate_st_clair_curve_for_line(line, tower=start).line_name == line.name
    _, foreign, _ = _routed_line()
    with pytest.raises(ValueError, match="does not belong"):
        calculate_line_electrical_parameters(line, tower=foreign)
    with pytest.raises(ValueError, match="does not belong"):
        calculate_st_clair_curve_for_line(line, tower=foreign)
