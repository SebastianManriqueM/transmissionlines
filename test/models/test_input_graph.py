from abc import ABC
from math import pi

import pytest
from infrasys import Component
from pydantic import ValidationError

from transmissionlines.builders.system import assemble_line_into_system
from transmissionlines.models.assets import AbstractTransmissionLine, CrossSectionTransmissionLine, RoutedTransmissionLine
from transmissionlines.models.cables import (
    BareConductorEquipment,
    BundleSpec,
    ConductorSpec,
    GroundWireSpec,
    InsulatorStringSpec,
)
from transmissionlines.models.common import Bus, GeographicPoint, IdentificationInfo
from transmissionlines.models.configurations import CircuitConfiguration, TowerConfiguration
from transmissionlines.models.geometry import GroundWirePosition, PhasePosition, TowerGeometry
from transmissionlines.models.routing import ElectricalTower, LineSpan, RouteGeometry, StartEnd
from transmissionlines.system import TransmissionLineSystem
from transmissionlines.units import Angle, BundleSpacing, EarthResistivity, Frequency, TowerCoordinate, VoltageKV


def _configuration() -> TowerConfiguration:
    conductor = ConductorSpec(name="conductor", equipment=BareConductorEquipment())
    ground = GroundWireSpec(name="ground", equipment=BareConductorEquipment())
    configuration = TowerConfiguration(
        name="standard",
        identification_info=IdentificationInfo(),
        geometry=TowerGeometry(
            phase_positions=[
                PhasePosition(circuit_id="c1", phase=phase, x=TowerCoordinate(0, "foot"), y=TowerCoordinate(30, "foot"))
                for phase in ("A", "B", "C")
            ],
            ground_wire_positions=[GroundWirePosition(wire_id="g1", x=TowerCoordinate(0, "foot"), y=TowerCoordinate(40, "foot"))],
        ),
        ground_wire_spec=ground,
        circuits=[CircuitConfiguration(
            name="c1", circuit_id="c1", conductor_spec=conductor,
            bundle_spec=BundleSpec(subconductor_count=1),
            insulator_string=InsulatorStringSpec(
                insulator_type="glass", number_of_insulators=12,
                insulator_code="U120B", insulator_coupling="ball_and_socket",
            ),
        )],
    )
    return configuration


def test_cross_section_requires_representative_configuration_without_route() -> None:
    configuration = _configuration()
    electrical = dict(
        name="cross",
        nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )

    assert issubclass(AbstractTransmissionLine, ABC)
    with pytest.raises(ValidationError, match="configuration"):
        CrossSectionTransmissionLine(**electrical)
    line = CrossSectionTransmissionLine(**electrical, configuration=configuration)
    assert line.configuration is configuration
    assert not {"spans", "from_bus", "to_bus", "line_parameters"} & set(type(line).model_fields)
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CrossSectionTransmissionLine(**electrical, configuration=configuration, spans=[])


def _point(longitude: float) -> GeographicPoint:
    return GeographicPoint(latitude=Angle(45, "degree"), longitude=Angle(longitude, "degree"))


def _route() -> tuple[Bus, Bus, ElectricalTower, ElectricalTower, LineSpan]:
    configuration = _configuration()
    start = ElectricalTower(
        name="route:tower:000", tower_id="T0", sequence=0, location=_point(-108),
        configuration=configuration, structure_form="lattice", support_role="terminal",
    )
    end = ElectricalTower(
        name="route:tower:001", tower_id="T1", sequence=1, location=_point(-107),
        configuration=configuration, structure_form="pole", support_role="terminal",
    )
    span = LineSpan(
        name="route:span:000", span_id="S0", sequence=0,
        start_end=StartEnd(name="route:span:000:endpoints", start=start, end=end),
        route_geometry=RouteGeometry(coordinates=[(-108, 45), (-107, 45)]),
    )
    return Bus(name="from", location=_point(-108)), Bus(name="to", location=_point(-107)), start, end, span


@pytest.mark.parametrize(
    ("latitude", "longitude", "invalid_field"),
    [(95, 0, "latitude"), (0, 200, "longitude")],
)
def test_bus_and_tower_reject_out_of_range_wgs84_locations(
    latitude: float, longitude: float, invalid_field: str,
) -> None:
    location = dict(latitude=Angle(latitude, "degree"), longitude=Angle(longitude, "degree"))
    with pytest.raises(ValidationError, match=invalid_field):
        Bus(name="invalid-bus", location=location)
    with pytest.raises(ValidationError, match=invalid_field):
        ElectricalTower(
            name="invalid-tower", tower_id="T1", sequence=0, location=location,
            configuration=_configuration(), structure_form="pole", support_role="terminal",
        )


def test_wgs84_boundaries_accept_radian_coordinates() -> None:
    location = GeographicPoint(latitude=Angle(pi / 2, "radian"), longitude=Angle(-pi, "radian"))
    assert Bus(name="boundary", location=location).location is location
    assert ElectricalTower(
        name="boundary-tower", tower_id="T1", sequence=0, location=location,
        configuration=_configuration(), structure_form="pole", support_role="terminal",
    ).location is location


def test_routed_line_requires_real_ordered_spans_and_terminal_towers() -> None:
    from_bus, to_bus, start, end, span = _route()
    electrical = dict(
        name="route", nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
        from_bus=from_bus, to_bus=to_bus,
    )
    line = RoutedTransmissionLine(**electrical, spans=[span])

    assert line.spans[0].start_end.start is start
    assert line.spans[0].start_end.end is end
    assert not {"configuration", "towers", "line_parameters"} & set(type(line).model_fields)
    with pytest.raises(ValidationError, match="nonempty"):
        RoutedTransmissionLine(**electrical, spans=[])
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RoutedTransmissionLine(**electrical, spans=[span], configuration=start.configuration)
    with pytest.raises(ValidationError, match="terminal"):
        RoutedTransmissionLine(
            **electrical,
            spans=[span.model_copy(update={"start_end": StartEnd(name="other", start=start.model_copy(update={"support_role": "suspension"}), end=end)})],
        )


def test_routed_line_rejects_disconnected_or_mismatched_geometry() -> None:
    from_bus, to_bus, start, end, span = _route()
    electrical = dict(
        name="route", nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
        from_bus=from_bus, to_bus=to_bus,
    )
    with pytest.raises(ValidationError, match="endpoint"):
        RoutedTransmissionLine(**electrical, spans=[span.model_copy(update={
            "route_geometry": RouteGeometry(coordinates=[(-108, 45), (-106, 45)])
        })])
    with pytest.raises(ValidationError, match="distinct supports"):
        RoutedTransmissionLine(**electrical, spans=[span, span])


def test_route_rejects_missing_physical_roles_duplicate_ids_and_same_endpoints() -> None:
    _, _, start, end, span = _route()
    with pytest.raises(ValidationError, match="support_role"):
        ElectricalTower(
            name="missing-role", tower_id="T2", sequence=2, location=_point(-106),
            configuration=start.configuration, structure_form="pole",
        )
    with pytest.raises(ValidationError, match="span endpoint towers must differ"):
        StartEnd(name="same", start=start, end=start)
    with pytest.raises(ValidationError, match="route_geometry"):
        RouteGeometry(coordinates=[(-108, 45)])
    with pytest.raises(ValidationError, match="span"):
        RoutedTransmissionLine(
            name="route", from_bus=Bus(name="from", location=start.location),
            to_bus=Bus(name="to", location=end.location),
            spans=[span.model_copy(update={"sequence": 1})],
            nominal_voltage=VoltageKV(230, "kilovolt"),
            nominal_frequency=Frequency(60, "hertz"),
            earth_resistivity=EarthResistivity(100, "ohm * meter"),
        )


def test_multiple_spans_require_shared_join_and_unique_support_and_span_ids() -> None:
    from_bus, _, start, middle, first = _route()
    end = ElectricalTower(
        name="route:tower:002", tower_id="T2", sequence=2, location=_point(-106),
        configuration=middle.configuration, structure_form="pole", support_role="terminal",
    )
    second = LineSpan(
        name="route:span:001", span_id="S1", sequence=1,
        start_end=StartEnd(name="route:span:001:endpoints", start=middle, end=end),
        route_geometry=RouteGeometry(coordinates=[(-107, 45), (-106, 45)]),
    )
    electrical = dict(
        name="route", from_bus=from_bus, to_bus=Bus(name="to", location=end.location),
        nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )
    assert len(RoutedTransmissionLine(**electrical, spans=[first, second]).spans) == 2
    other_middle = ElectricalTower(
        name="different", tower_id="other", sequence=1, location=middle.location,
        configuration=middle.configuration, structure_form="pole", support_role="suspension",
    )
    disconnected = second.model_copy(update={"start_end": StartEnd(
        name="different-endpoints", start=other_middle, end=end,
    )})
    with pytest.raises(ValidationError, match="adjacent"):
        RoutedTransmissionLine(**electrical, spans=[first, disconnected])
    repeated_span = second.model_copy(update={"span_id": "S0"})
    with pytest.raises(ValidationError, match="span_id"):
        RoutedTransmissionLine(**electrical, spans=[first, repeated_span])
    repeated_tower = end.model_copy(update={"tower_id": "T0"})
    repeated_end = second.model_copy(update={"start_end": StartEnd(
        name="repeated-endpoints", start=middle, end=repeated_tower,
    )})
    with pytest.raises(ValidationError, match="tower_id"):
        RoutedTransmissionLine(**electrical, spans=[first, repeated_end])


def test_routed_line_accepts_different_tower_configurations_without_line_configuration() -> None:
    from_bus, _, start, end, span = _route()
    second = _configuration().model_copy(update={"name": "alternate"})
    end = end.model_copy(update={"configuration": second})
    span = span.model_copy(update={"start_end": StartEnd(name="new-endpoints", start=start, end=end)})
    line = RoutedTransmissionLine(
        name="route", from_bus=from_bus, to_bus=Bus(name="to", location=end.location),
        spans=[span], nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )

    assert line.spans[0].start_end.start.configuration.name == "standard"
    assert line.spans[0].start_end.end.configuration.name == "alternate"
    system = TransmissionLineSystem(name="different-configurations")
    registered = assemble_line_into_system(system, line)
    assert registered.spans[0].start_end.start.configuration is system.get_component(TowerConfiguration, "standard")
    assert registered.spans[0].start_end.end.configuration is system.get_component(TowerConfiguration, "alternate")


def test_registered_circuits_can_share_one_conductor_after_reload(tmp_path) -> None:
    configuration = _configuration()
    geometry = configuration.geometry
    second_positions = [
        PhasePosition(circuit_id="c2", phase=phase, x=TowerCoordinate(10, "foot"), y=TowerCoordinate(30, "foot"))
        for phase in ("A", "B", "C")
    ]
    second = CircuitConfiguration(
        name="c2", circuit_id="c2", conductor_spec=configuration.circuits[0].conductor_spec,
        bundle_spec=BundleSpec(subconductor_count=1),
        insulator_string=configuration.circuits[0].insulator_string,
    )
    configuration = configuration.model_copy(update={
        "geometry": TowerGeometry(
            phase_positions=[*geometry.phase_positions, *second_positions],
            ground_wire_positions=geometry.ground_wire_positions,
        ),
        "circuits": [*configuration.circuits, second],
    })
    line = CrossSectionTransmissionLine(
        name="shared-cable", configuration=configuration,
        nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )
    system = TransmissionLineSystem(name="shared-cable")
    assemble_line_into_system(system, line)
    assert len(list(system.get_components(ConductorSpec))) == 1
    path = tmp_path / "shared-cable.json"
    system.to_json(path, overwrite=True)
    loaded = TransmissionLineSystem.from_json(path)
    circuits = loaded.get_component(CrossSectionTransmissionLine, "shared-cable").configuration.circuits
    assert circuits[0].conductor_spec is circuits[1].conductor_spec
    assert circuits[0].conductor_spec is loaded.get_component(ConductorSpec, "conductor")


def test_builder_reuses_identical_configuration_and_rejects_conflicts_before_mutation() -> None:
    system = TransmissionLineSystem(name="inputs")
    electrical = dict(
        nominal_voltage=VoltageKV(230, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )
    first = assemble_line_into_system(system, CrossSectionTransmissionLine(
        name="first", configuration=_configuration(), **electrical,
    ))
    second = assemble_line_into_system(system, CrossSectionTransmissionLine(
        name="second", configuration=_configuration(), **electrical,
    ))
    assert first.configuration is second.configuration
    before = len(list(system.get_components(Component)))
    conflicting = _configuration().model_copy(update={"identification_info": IdentificationInfo(geometry_id="different")})
    with pytest.raises(ValueError, match="component-name conflict"):
        assemble_line_into_system(system, CrossSectionTransmissionLine(
            name="third", configuration=conflicting, **electrical,
        ))
    assert len(list(system.get_components(Component))) == before
    colliding = CrossSectionTransmissionLine(
        name="other", uuid=first.uuid, configuration=_configuration(), **electrical,
    )
    with pytest.raises(ValueError, match="component-uuid conflict"):
        assemble_line_into_system(system, colliding)
    assert len(list(system.get_components(Component))) == before


def test_configuration_shares_conductor_but_keeps_bundle_and_insulator_per_circuit() -> None:
    conductor = ConductorSpec(name="shared", equipment=BareConductorEquipment())
    insulator = InsulatorStringSpec(
        insulator_type="glass", number_of_insulators=12,
        insulator_code="U120B", insulator_coupling="ball_and_socket",
    )
    circuit_a = CircuitConfiguration(
        name="a", circuit_id="a", conductor_spec=conductor,
        bundle_spec=BundleSpec(subconductor_count=1), insulator_string=insulator,
    )
    circuit_b = CircuitConfiguration(
        name="b", circuit_id="b", conductor_spec=conductor,
        bundle_spec=BundleSpec(subconductor_count=2, subconductor_spacing=BundleSpacing(18, "inch")),
        insulator_string=insulator,
    )

    assert circuit_a.conductor_spec is circuit_b.conductor_spec
    assert circuit_a.bundle_spec != circuit_b.bundle_spec
    with pytest.raises(ValidationError, match="subconductor_spacing"):
        BundleSpec(subconductor_count=2)
    with pytest.raises(ValidationError, match="number_of_insulators"):
        InsulatorStringSpec(
            insulator_type="glass", number_of_insulators=0,
            insulator_code="U120B", insulator_coupling="ball_and_socket",
        )


@pytest.mark.parametrize("variant", ["cross", "route"])
def test_builder_registers_only_selected_input_graph_and_round_trips(variant: str, tmp_path) -> None:
    if variant == "cross":
        line = CrossSectionTransmissionLine(
            name="cross", configuration=_configuration(), nominal_voltage=VoltageKV(230, "kilovolt"),
            nominal_frequency=Frequency(60, "hertz"), earth_resistivity=EarthResistivity(100, "ohm * meter"),
        )
    else:
        from_bus, to_bus, _, _, span = _route()
        line = RoutedTransmissionLine(
            name="route", from_bus=from_bus, to_bus=to_bus, spans=[span],
            nominal_voltage=VoltageKV(230, "kilovolt"), nominal_frequency=Frequency(60, "hertz"),
            earth_resistivity=EarthResistivity(100, "ohm * meter"),
        )
    system = TransmissionLineSystem(name="input")
    registered = assemble_line_into_system(system, line)
    assert registered is system.get_component(type(line), line.name)
    assert len(list(system.get_components(ElectricalTower))) == (0 if variant == "cross" else 2)
    assert len(list(system.get_components(ConductorSpec))) == 1
    assert len(list(system.get_components(CircuitConfiguration))) == 1
    path = tmp_path / "input.json"
    system.to_json(path, overwrite=True)
    assert '"line_parameters"' not in path.read_text()
    assert '"span_length"' not in path.read_text()
    assert '"bundle_gmr"' not in path.read_text()

    loaded = TransmissionLineSystem.from_json(path)
    restored = loaded.get_component(type(line), line.name)
    configuration = (restored.configuration if variant == "cross"
                     else restored.spans[0].start_end.start.configuration)
    assert configuration is loaded.get_component(TowerConfiguration, "standard")
    assert configuration.circuits[0] is loaded.get_component(CircuitConfiguration, "c1")
    assert configuration.circuits[0].conductor_spec is loaded.get_component(ConductorSpec, "conductor")
    if variant == "route":
        assert restored.spans[0].start_end.start is loaded.get_component(ElectricalTower, "route:tower:000")