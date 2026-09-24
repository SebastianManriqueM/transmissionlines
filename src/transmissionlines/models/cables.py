"""Immutable cable and tower geometry models."""

from pydantic import computed_field, model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.common import CatalogReference, GroundWirePosition, PhasePosition
from transmissionlines.units import (
    BundleSpacing,
    CableDiameter,
    CableGMR,
    Current,
    EquivalentRadius,
    ResistancePerKft,
)


class BareConductorEquipment(LineDataModel):
    """Measured or manufacturer-provided conductor properties."""

    conductor_diameter: CableDiameter | None = None
    conductor_gmr: CableGMR | None = None
    ampacity: Current | None = None
    ac_resistance: ResistancePerKft | None = None
    emergency_ampacity: Current | None = None
    dc_resistance: ResistancePerKft | None = None


class CableSpec(LineDataModel):
    """Selected cable and its provenance."""

    conductor: BareConductorEquipment
    catalog_reference: CatalogReference | None = None


class GroundWireSpec(CableSpec):
    """One shared, unbundled ground wire."""


class PhaseConductorSpec(CableSpec):
    """Conductor selection for all three phases of a circuit."""

    circuit_id: str
    subconductor_count: int = 1
    subconductor_spacing: BundleSpacing | None = None

    @model_validator(mode="after")
    def validate_bundle(self) -> "PhaseConductorSpec":
        if self.subconductor_count < 1:
            raise ValueError("subconductor_count must be positive")
        if self.subconductor_count > 1 and (
            self.subconductor_spacing is None or self.subconductor_spacing.magnitude <= 0
        ):
            raise ValueError("subconductor_spacing is required and positive for bundles")
        if self.subconductor_count == 1 and self.subconductor_spacing is not None:
            raise ValueError("single conductors cannot specify subconductor_spacing")
        return self

    @computed_field
    @property
    def bundle_gmr(self) -> CableGMR | None:
        """Return the bundle GMR when source GMR and spacing are available."""
        gmr = self.conductor.conductor_gmr
        if gmr is None or self.subconductor_count == 1:
            return gmr
        assert self.subconductor_spacing is not None
        spacing = self.subconductor_spacing.to("foot")
        return CableGMR(
            (gmr.to("foot").magnitude * spacing.magnitude ** (self.subconductor_count - 1))
            ** (1 / self.subconductor_count),
            "foot",
        )

    @computed_field
    @property
    def equivalent_radius(self) -> EquivalentRadius | None:
        """Return equivalent conductor radius when diameter is known."""
        diameter = self.conductor.conductor_diameter
        if diameter is None:
            return None
        if self.subconductor_count == 1:
            return EquivalentRadius(diameter.to("foot").magnitude / 2, "foot")
        assert self.subconductor_spacing is not None
        spacing = self.subconductor_spacing.to("foot")
        radius = diameter.to("foot").magnitude / 2
        return EquivalentRadius(
            (radius * spacing.magnitude ** (self.subconductor_count - 1))
            ** (1 / self.subconductor_count),
            "foot",
        )


class TowerGeometry(LineDataModel):
    """Complete tower-local phase and ground-wire geometry."""

    phase_positions: list[PhasePosition]
    ground_wire_positions: list[GroundWirePosition]

    @model_validator(mode="after")
    def validate_geometry(self) -> "TowerGeometry":
        groups: dict[str, list[str]] = {}
        for position in self.phase_positions:
            groups.setdefault(position.circuit_id, []).append(position.phase)
        if not groups or any(sorted(phases) != ["A", "B", "C"] for phases in groups.values()):
            raise ValueError(
                "each configured circuit must have exactly A, B, and C phase positions"
            )
        if not self.ground_wire_positions:
            raise ValueError("at least one ground-wire position is required")
        return self


__all__ = [
    "BareConductorEquipment",
    "CableSpec",
    "GroundWireSpec",
    "PhaseConductorSpec",
    "TowerGeometry",
]
