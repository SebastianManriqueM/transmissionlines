"""Explicit system assembly for v3 static components."""

from pydantic import BaseModel

from transmissionlines.models import Bus, GeographicPoint, TowerConfiguration, TransmissionLine
from transmissionlines.system import TransmissionLineSystem


class BusDefinition(BaseModel):
    """User-supplied name and location used during assembly."""

    name: str
    location: GeographicPoint


def _compatible(left: object, right: object) -> bool:
    """Compare Pydantic values and quantities semantically."""
    if hasattr(left, "units") and hasattr(right, "to"):
        try:
            return left == right
        except (TypeError, ValueError):
            return False
    if isinstance(left, BaseModel) and isinstance(right, BaseModel):
        if set(left.model_fields) != set(right.model_fields):
            return False
        return all(
            _compatible(getattr(left, field), getattr(right, field)) for field in left.model_fields
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_compatible(a, b) for a, b in zip(left, right))
    return left == right


def build_transmission_line(
    request: TransmissionLine, *, tower_configuration: TowerConfiguration | None = None
) -> TransmissionLine:
    """Construct a line without mutating any system."""
    if tower_configuration is None:
        return request
    return request.model_copy(update={"tower_configuration": tower_configuration})


def assemble_line_into_system(
    system: TransmissionLineSystem,
    line: TransmissionLine,
    *,
    from_bus: BusDefinition,
    to_bus: BusDefinition,
) -> TransmissionLine:
    """Resolve/create terminals and reusable configuration, then register a line."""
    if from_bus.name == to_bus.name:
        raise ValueError("from_bus and to_bus must be distinct")
    buses = []
    for definition in (from_bus, to_bus):
        try:
            existing = system.get_component(Bus, definition.name)
        except Exception:
            existing = None
        if existing is None:
            existing = Bus(name=definition.name, location=definition.location)
            system.add_component(existing)
        elif not _compatible(existing.location, definition.location):
            raise ValueError(f"bus-definition conflict for {definition.name!r}")
        buses.append(existing)
    config = line.tower_configuration
    try:
        existing_config = system.get_component(TowerConfiguration, config.name)
    except Exception:
        existing_config = None
    if existing_config is None:
        system.add_component(config)
        resolved_config = config
    elif not _compatible(existing_config, config):
        raise ValueError(f"configuration-name conflict for {config.name!r}")
    else:
        resolved_config = existing_config
    info = line.technical_info.model_copy(update={"from_bus": buses[0], "to_bus": buses[1]})
    resolved = line.model_copy(
        update={"technical_info": info, "tower_configuration": resolved_config}
    )
    if resolved.routing_info is not None:
        system.add_components(*resolved.routing_info.towers, *resolved.routing_info.spans)
    system.add_component(resolved)
    return resolved


__all__ = ["BusDefinition", "assemble_line_into_system", "build_transmission_line"]
