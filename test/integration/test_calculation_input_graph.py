import pytest

from transmissionlines.calculations.electrical import calculate_line_electrical_parameters
from transmissionlines.calculations.st_clair import calculate_st_clair_curve_for_line
from transmissionlines.models.assets import CrossSectionTransmissionLine, RoutedTransmissionLine
from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec, GroundWireSpec, InsulatorStringSpec
from transmissionlines.models.common import Bus, GeographicPoint, IdentificationInfo
from transmissionlines.models.configurations import CircuitConfiguration, TowerConfiguration
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.models.routing import ElectricalTower, LineSpan, RouteGeometry, StartEnd
from transmissionlines.units import Angle, CableDiameter, CableGMR, Current, EarthResistivity, Frequency, ResistancePerKft, TowerCoordinate, VoltageKV


def _configuration() -> TowerConfiguration:
    equipment = BareConductorEquipment(
        conductor_diameter=CableDiameter(1, "inch"),
        conductor_gmr=CableGMR(0.04, "foot"),
        ampacity=Current(1000, "ampere"),
        ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot"),
        dc_resistance=ResistancePerKft(0.2, "ohm / kilofoot"),
    )
    return TowerConfiguration(
        name="configuration", identification_info=IdentificationInfo(),
        geometry=TowerGeometry(
            phase_positions=[
                PhasePosition(circuit_id="c1", phase=phase, x=TowerCoordinate(index * 4, "foot"), y=TowerCoordinate(30, "foot"))
                for index, phase in enumerate(("A", "B", "C"))
            ],
            ground_wire_positions=[GroundWirePosition(wire_id="g1", x=TowerCoordinate(0, "foot"), y=TowerCoordinate(40, "foot"))],
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
        nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )
    result = calculate_line_electrical_parameters(line)
    assert result.line_uuid == line.uuid
    assert result.configuration_uuid == line.configuration.uuid
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
        GeographicPoint(latitude=Angle(45, "degree"), longitude=Angle(longitude, "degree"))
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
        nominal_voltage=VoltageKV(230, "kilovolt"), nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )
    return line, start, end


def test_routed_shared_configuration_returns_selected_cross_section() -> None:
    line, start, _ = _routed_line()
    result = calculate_line_electrical_parameters(line)
    assert result.configuration_uuid == start.configuration.uuid
    assert result.electrical.status == "complete"
    assert result.st_clair is not None
    assert "line_parameters" not in type(line).model_fields


def test_routed_heterogeneous_requires_owned_tower_and_matching_prior_result() -> None:
    line, start, end = _routed_line(different=True)
    with pytest.raises(ValueError, match="select a tower"):
        calculate_line_electrical_parameters(line)
    result = calculate_line_electrical_parameters(line, tower=end)
    assert result.configuration_uuid == end.configuration.uuid
    assert calculate_st_clair_curve_for_line(line, result, tower=end).line_name == line.name
    with pytest.raises(ValueError, match="does not match"):
        calculate_st_clair_curve_for_line(line, result, tower=start)
    other_line, foreign, _ = _routed_line()
    with pytest.raises(ValueError, match="does not belong"):
        calculate_line_electrical_parameters(line, tower=foreign)
    with pytest.raises(ValueError, match="does not match"):
        calculate_st_clair_curve_for_line(other_line, result)
    altered_electrical = result.electrical.model_copy(update={"circuit_scalars": {"foreign": result.electrical.circuit_scalars["c1"]}})
    altered_result = result.model_copy(update={"electrical": altered_electrical})
    with pytest.raises(ValueError, match="circuit IDs"):
        calculate_st_clair_curve_for_line(line, altered_result, tower=end)