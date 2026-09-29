"""Register validated transmission-line input graphs in an Infrasys system."""

from infrasys import Component
from infrasys.exceptions import ISNotStored
from pydantic import BaseModel

from transmissionlines.models.assets import AbstractTransmissionLine
from transmissionlines.system import TransmissionLineSystem


def _compatible(left: object, right: object) -> bool:
    if isinstance(left, Component) and isinstance(right, Component):
        if type(left) is not type(right):
            return False
    if isinstance(left, BaseModel) and isinstance(right, BaseModel):
        return type(left) is type(right) and all(
            _compatible(getattr(left, field), getattr(right, field))
            for field in type(left).model_fields if field != "uuid"
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(
            _compatible(first, second) for first, second in zip(left, right)
        )
    return left == right


def _canonicalize(
    system: TransmissionLineSystem,
    component: Component,
    candidates: dict[tuple[type[Component], str], Component],
    additions: list[Component],
) -> Component:
    changes = {}
    for field in type(component).model_fields:
        value = getattr(component, field)
        if isinstance(value, Component):
            changes[field] = _canonicalize(system, value, candidates, additions)
        elif isinstance(value, list) and value and all(isinstance(item, Component) for item in value):
            changes[field] = [_canonicalize(system, item, candidates, additions) for item in value]
    candidate = component.model_copy(update=changes) if changes else component
    key = (type(candidate), candidate.name)
    try:
        uuid_owner = system.get_component_by_uuid(candidate.uuid)
    except ISNotStored:
        uuid_owner = None
    if uuid_owner is not None and (type(uuid_owner), uuid_owner.name) != key:
        raise ValueError(f"component-uuid conflict for {type(candidate).__name__} {candidate.name!r}")
    if any(
        proposed.uuid == candidate.uuid and (type(proposed), proposed.name) != key
        for proposed in additions
    ):
        raise ValueError(f"component-uuid conflict for {type(candidate).__name__} {candidate.name!r}")
    existing = candidates.get(key)
    if existing is None:
        try:
            existing = system.get_component(type(candidate), candidate.name)
        except ISNotStored:
            existing = None
    if existing is not None:
        if not _compatible(existing, candidate):
            raise ValueError(f"component-name conflict for {type(candidate).__name__} {candidate.name!r}")
        return existing
    candidates[key] = candidate
    additions.append(candidate)
    return candidate


def build_transmission_line(line: AbstractTransmissionLine) -> AbstractTransmissionLine:
    """Return a validated concrete input line without mutating a system.

    Parameters
    ----------
    line : AbstractTransmissionLine
        Cross-section or routed input line.

    Returns
    -------
    AbstractTransmissionLine
        The same input line.
    """
    return line


def assemble_line_into_system(
    system: TransmissionLineSystem, line: AbstractTransmissionLine
) -> AbstractTransmissionLine:
    """Preflight and register the selected input graph using canonical references.

    Parameters
    ----------
    system : TransmissionLineSystem
        Destination system.
    line : AbstractTransmissionLine
        Concrete line with validated component references.

    Returns
    -------
    AbstractTransmissionLine
        Registered line with canonical shared references.

    Raises
    ------
    ValueError
        When an existing type/name has incompatible static inputs.
    """
    candidates: dict[tuple[type[Component], str], Component] = {}
    additions: list[Component] = []
    resolved = _canonicalize(system, line, candidates, additions)
    if resolved is not additions[-1]:
        raise ValueError(f"line {line.name!r} is already registered")
    system.add_components(*additions)
    return resolved


__all__ = ["assemble_line_into_system", "build_transmission_line"]