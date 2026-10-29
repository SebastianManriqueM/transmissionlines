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
from transmissionlines.units import Amperes, Feet, Kilovolts, Quantity


class ProbeValue(LineDataModel):
    """Embedded value used to prove value-model serialization."""

    label: str
    clearance_ft: Feet


class ProbeBus(Component):
    """Minimal registered component for foundation tests."""

    location: ProbeValue


class ProbeLine(Component):
    """Minimal component with component references and nested values."""

    from_bus: ProbeBus
    to_bus: ProbeBus
    design_voltage_kv: Kilovolts
    embedded: ProbeValue


class ProbeAttribute(OperationAttribute):
    """Minimal operational supplemental attribute for foundation tests."""

    metric_name: str
    nominal_current_a: Amperes


class NestedReferenceValue(LineDataModel):
    """Value shape used to document Infrasys nested-reference limitations."""

    owner: ProbeBus


class ProbeNestedReferenceLine(Component):
    """Component with a nested value model that contains a component reference."""

    nested: NestedReferenceValue


def test_line_data_model_is_frozen_and_rejects_extra_fields() -> None:
    value = ProbeValue(label="clearance", clearance_ft=12)

    with pytest.raises(ValidationError, match="frozen"):
        value.label = "mutated"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProbeValue(label="clearance", clearance_ft=12, extra=1)  # type: ignore[call-arg]


def test_component_names_are_required_and_immutable_but_attributes_are_unnamed() -> None:
    value = ProbeValue(label="substation", clearance_ft=1)
    bus = ProbeBus(name="bus-a", location=value)
    attribute = ProbeAttribute(metric_name="rating", nominal_current_a=500)

    assert bus.name == "bus-a"
    assert not hasattr(attribute, "name")

    with pytest.raises(ValidationError, match="Field required"):
        ProbeBus(location=value)  # type: ignore[call-arg]

    with pytest.raises(ValidationError, match="frozen"):
        bus.name = "other"


def test_unit_named_floats_survive_json_round_trip(
    tmp_path: Path,
) -> None:
    system = TransmissionLineSystem(name="quantity-test")
    bus_a = ProbeBus(
        name="bus-a",
        location=ProbeValue(label="a", clearance_ft=Quantity(36, "inch")),
    )
    bus_b = ProbeBus(
        name="bus-b",
        location=ProbeValue(label="b", clearance_ft=2),
    )
    line = ProbeLine(
        name="line-a-b",
        from_bus=bus_a,
        to_bus=bus_b,
        design_voltage_kv=230,
        embedded=ProbeValue(label="embedded", clearance_ft=1.5),
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
    assert loaded_line.design_voltage_kv == 230
    assert loaded_line.embedded.clearance_ft == 1.5
    assert loaded_line.from_bus.location.clearance_ft == 3.0


def test_supplemental_attribute_and_time_series_sidecar_round_trip(tmp_path: Path) -> None:
    system = TransmissionLineSystem(name="attribute-test")
    bus = ProbeBus(
        name="bus-a",
        location=ProbeValue(label="a", clearance_ft=1),
    )
    attribute = ProbeAttribute(metric_name="rating", nominal_current_a=750)
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
    assert loaded_attribute.nominal_current_a == 750
    assert list(loaded_series.data.magnitude) == [700.0, 710.0]
    assert str(loaded_series.data.units) == "ampere"


def test_legacy_system_format_is_rejected(tmp_path: Path) -> None:
    system = TransmissionLineSystem(name="schema-test")
    bus = ProbeBus(
        name="bus-a",
        location=ProbeValue(label="a", clearance_ft=1),
    )
    system.add_component(bus)
    path = tmp_path / "system.json"
    system.to_json(path, overwrite=True)

    import orjson

    data: dict[str, Any] = orjson.loads(path.read_bytes())
    data["data_format_version"] = "2.0.0"
    data["transmissionlines_schema_version"] = "2.0.0"
    path.write_bytes(orjson.dumps(data))

    from infrasys.exceptions import ISOperationNotAllowed

    with pytest.raises(ISOperationNotAllowed, match="Unsupported transmission-line system data format"):
        TransmissionLineSystem.from_json(path)


def test_legacy_package_schema_is_rejected_when_infrasys_format_is_current(
    tmp_path: Path,
) -> None:
    system = TransmissionLineSystem(name="schema-test")
    system.add_component(
        ProbeBus(
            name="bus-a",
            location=ProbeValue(label="a", clearance_ft=1),
        )
    )
    path = tmp_path / "legacy-package-schema.json"
    system.to_json(path, overwrite=True)

    import orjson

    data: dict[str, Any] = orjson.loads(path.read_bytes())
    data["data_format_version"] = SCHEMA_VERSION
    data["transmissionlines_schema_version"] = "2.0.0"
    path.write_bytes(orjson.dumps(data))

    from infrasys.exceptions import ISOperationNotAllowed

    with pytest.raises(ISOperationNotAllowed, match="Unsupported transmission-line package schema"):
        TransmissionLineSystem.from_json(path)


def test_unknown_package_schema_is_rejected_when_infrasys_format_is_current(
    tmp_path: Path,
) -> None:
    system = TransmissionLineSystem(name="schema-test")
    system.add_component(
        ProbeBus(
            name="bus-a",
            location=ProbeValue(label="a", clearance_ft=1),
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
        location=ProbeValue(label="a", clearance_ft=1),
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


@pytest.mark.parametrize("ampacity", [0.0, -1.0, float("nan"), float("inf")])
def test_conductor_equipment_rejects_nonpositive_measurements(ampacity: float) -> None:
    from transmissionlines.models.cables import BareConductorEquipment

    assert BareConductorEquipment(ampacity_a=None).ampacity_a is None
    with pytest.raises(ValidationError, match="ampacity_a must be finite and positive"):
        BareConductorEquipment(ampacity_a=ampacity)


def test_unit_fields_store_floats_and_convert_quantities() -> None:
    from transmissionlines.models.cables import BundleSpec
    from transmissionlines.models.geometry import CablePosition

    assert CablePosition(x_ft=3, y_ft=30).x_ft == 3.0
    assert CablePosition(x_ft=Quantity(1, "meter"), y_ft=30).x_ft == pytest.approx(3.28084, rel=1e-5)
    assert BundleSpec(subconductor_count=2, subconductor_spacing_in=Quantity(1.5, "foot")).subconductor_spacing_in == 18
    with pytest.raises(ValidationError, match="expected a quantity convertible to foot"):
        CablePosition(x_ft=Quantity(1, "second"), y_ft=30)
