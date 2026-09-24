from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from infrasys import Component, SingleTimeSeries
from infrasys.base_quantity import ureg
from pydantic import ValidationError

from transmissionlines.models.base import LineDataModel, OperationAttribute
from transmissionlines.system import SCHEMA_VERSION, TransmissionLineSystem
from transmissionlines.units import Current, TowerCoordinate, VoltageKV


class ProbeValue(LineDataModel):
    """Embedded value used to prove value-model serialization."""

    label: str
    clearance: TowerCoordinate


class ProbeBus(Component):
    """Minimal registered component for foundation tests."""

    location: ProbeValue


class ProbeLine(Component):
    """Minimal component with component references and nested quantities."""

    from_bus: ProbeBus
    to_bus: ProbeBus
    design_voltage: VoltageKV
    embedded: ProbeValue


class ProbeAttribute(OperationAttribute):
    """Minimal operational supplemental attribute for foundation tests."""

    metric_name: str
    nominal_current: Current


class NestedReferenceValue(LineDataModel):
    """Value shape used to document Infrasys nested-reference limitations."""

    owner: ProbeBus


class ProbeNestedReferenceLine(Component):
    """Component with a nested value model that contains a component reference."""

    nested: NestedReferenceValue


def test_line_data_model_is_frozen_and_rejects_extra_fields() -> None:
    value = ProbeValue(label="clearance", clearance=TowerCoordinate(12, "foot"))

    with pytest.raises(ValidationError, match="frozen"):
        value.label = "mutated"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProbeValue(label="clearance", clearance=TowerCoordinate(12, "foot"), extra=1)  # type: ignore[call-arg]


def test_component_names_are_required_and_immutable_but_attributes_are_unnamed() -> None:
    value = ProbeValue(label="substation", clearance=TowerCoordinate(1, "foot"))
    bus = ProbeBus(name="bus-a", location=value)
    attribute = ProbeAttribute(metric_name="rating", nominal_current=Current(500, "ampere"))

    assert bus.name == "bus-a"
    assert not hasattr(attribute, "name")

    with pytest.raises(ValidationError, match="Field required"):
        ProbeBus(location=value)  # type: ignore[call-arg]

    with pytest.raises(ValidationError, match="frozen"):
        bus.name = "other"


def test_project_quantities_share_infrasys_registry_and_preserve_units_in_json_round_trip(
    tmp_path: Path,
) -> None:
    system = TransmissionLineSystem(name="quantity-test")
    bus_a = ProbeBus(
        name="bus-a",
        location=ProbeValue(label="a", clearance=TowerCoordinate(36, "inch")),
    )
    bus_b = ProbeBus(
        name="bus-b",
        location=ProbeValue(label="b", clearance=TowerCoordinate(2, "foot")),
    )
    line = ProbeLine(
        name="line-a-b",
        from_bus=bus_a,
        to_bus=bus_b,
        design_voltage=VoltageKV(230, "kilovolt"),
        embedded=ProbeValue(label="embedded", clearance=TowerCoordinate(1.5, "foot")),
    )
    system.add_components(bus_a, bus_b, line)

    path = tmp_path / "system.json"
    system.to_json(path, overwrite=True)

    loaded = TransmissionLineSystem.from_json(path)
    loaded_line = loaded.get_component(ProbeLine, "line-a-b")

    assert loaded.data_format_version == SCHEMA_VERSION
    assert loaded.schema_version == SCHEMA_VERSION
    assert loaded_line.from_bus is loaded.get_component(ProbeBus, "bus-a")
    assert loaded_line.to_bus is loaded.get_component(ProbeBus, "bus-b")
    assert loaded_line.design_voltage.units == ureg.Unit("kilovolt")
    assert loaded_line.design_voltage.magnitude == 230
    assert loaded_line.embedded.clearance.units == ureg.Unit("foot")
    assert loaded_line.embedded.clearance.magnitude == 1.5
    assert TowerCoordinate._REGISTRY is ureg
    assert VoltageKV._REGISTRY is ureg


def test_supplemental_attribute_and_time_series_sidecar_round_trip(tmp_path: Path) -> None:
    system = TransmissionLineSystem(name="attribute-test")
    bus = ProbeBus(
        name="bus-a",
        location=ProbeValue(label="a", clearance=TowerCoordinate(1, "foot")),
    )
    attribute = ProbeAttribute(metric_name="rating", nominal_current=Current(750, "ampere"))
    samples = SingleTimeSeries(
        name="rating-samples",
        data=np.array([700.0, 710.0]) * ureg.ampere,
        resolution=timedelta(hours=1),
        initial_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    system.add_component(bus)
    system.add_supplemental_attribute(bus, attribute)
    system.add_time_series(samples, attribute)

    path = tmp_path / "system.json"
    system.to_json(path, overwrite=True)

    assert (tmp_path / "system_time_series").exists()

    loaded = TransmissionLineSystem.from_json(path)
    loaded_bus = loaded.get_component(ProbeBus, "bus-a")
    loaded_attribute = next(
        iter(loaded.get_supplemental_attributes_with_component(loaded_bus, ProbeAttribute))
    )
    loaded_series = loaded.get_time_series(loaded_attribute, "rating-samples")

    assert loaded_attribute.metric_name == "rating"
    assert loaded_attribute.nominal_current.units == ureg.Unit("ampere")
    assert list(loaded_series.data.magnitude) == [700.0, 710.0]
    assert str(loaded_series.data.units) == "ampere"


def test_schema_upgrade_hook_updates_legacy_metadata(tmp_path: Path) -> None:
    system = TransmissionLineSystem(name="schema-test")
    bus = ProbeBus(
        name="bus-a",
        location=ProbeValue(label="a", clearance=TowerCoordinate(1, "foot")),
    )
    system.add_component(bus)
    path = tmp_path / "system.json"
    system.to_json(path, overwrite=True)

    import orjson

    data: dict[str, Any] = orjson.loads(path.read_bytes())
    data["data_format_version"] = "2.0.0"
    data["transmissionlines_schema_version"] = "2.0.0"
    path.write_bytes(orjson.dumps(data))

    loaded = TransmissionLineSystem.from_json(path)

    assert loaded.data_format_version == SCHEMA_VERSION
    assert loaded.schema_version == SCHEMA_VERSION
    assert loaded.get_component(ProbeBus, "bus-a").name == "bus-a"


def test_legacy_package_schema_upgrades_when_infrasys_format_is_current(
    tmp_path: Path,
) -> None:
    system = TransmissionLineSystem(name="schema-test")
    system.add_component(
        ProbeBus(
            name="bus-a",
            location=ProbeValue(label="a", clearance=TowerCoordinate(1, "foot")),
        )
    )
    path = tmp_path / "legacy-package-schema.json"
    system.to_json(path, overwrite=True)

    import orjson

    data: dict[str, Any] = orjson.loads(path.read_bytes())
    data["data_format_version"] = SCHEMA_VERSION
    data["transmissionlines_schema_version"] = "2.0.0"
    path.write_bytes(orjson.dumps(data))

    loaded = TransmissionLineSystem.from_json(path)

    assert loaded.data_format_version == SCHEMA_VERSION
    assert loaded.schema_version == SCHEMA_VERSION


def test_unknown_package_schema_is_rejected_when_infrasys_format_is_current(
    tmp_path: Path,
) -> None:
    system = TransmissionLineSystem(name="schema-test")
    system.add_component(
        ProbeBus(
            name="bus-a",
            location=ProbeValue(label="a", clearance=TowerCoordinate(1, "foot")),
        )
    )
    path = tmp_path / "unknown-package-schema.json"
    system.to_json(path, overwrite=True)

    import orjson

    data: dict[str, Any] = orjson.loads(path.read_bytes())
    data["data_format_version"] = SCHEMA_VERSION
    data["transmissionlines_schema_version"] = "99.0.0"
    path.write_bytes(orjson.dumps(data))

    from infrasys.exceptions import ISOperationNotAllowed

    with pytest.raises(ISOperationNotAllowed, match="Unsupported transmission-line package schema"):
        TransmissionLineSystem.from_json(path)


def test_infrasys_does_not_round_trip_component_references_nested_inside_value_models(
    tmp_path: Path,
) -> None:
    system = TransmissionLineSystem(name="nested-reference-test")
    bus = ProbeBus(
        name="bus-a",
        location=ProbeValue(label="a", clearance=TowerCoordinate(1, "foot")),
    )
    line = ProbeNestedReferenceLine(name="line", nested=NestedReferenceValue(owner=bus))
    system.add_components(bus, line)

    path = tmp_path / "system.json"
    system.to_json(path, overwrite=True)

    loaded = TransmissionLineSystem.from_json(path)
    loaded_bus = loaded.get_component(ProbeBus, "bus-a")
    loaded_line = loaded.get_component(ProbeNestedReferenceLine, "line")

    assert loaded_line.nested.owner.uuid == loaded_bus.uuid
    assert loaded_line.nested.owner is not loaded_bus
