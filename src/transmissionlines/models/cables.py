"""Selected cable components and per-circuit installation inputs."""

from abc import ABC, abstractmethod
from typing import Literal

from infrasys import Component
from pydantic import model_validator

from transmissionlines.models.base import LineDataModel
from transmissionlines.models.common import CatalogReference
from transmissionlines.units import (
    BundleSpacing,
    CableDiameter,
    CableGMR,
    ConductorWeight,
    Current,
    MaterialArea,
    RatedBreakingStrength,
    ResistancePerKft,
)


class BareConductorEquipment(LineDataModel):
    """Measured or manufacturer-provided conductor properties."""

    conductor_diameter: CableDiameter | None = None
    conductor_gmr: CableGMR | None = None
    capacitance_radius: CableGMR | None = None
    ampacity: Current | None = None
    ac_resistance: ResistancePerKft | None = None
    emergency_ampacity: Current | None = None
    dc_resistance: ResistancePerKft | None = None
    weight: ConductorWeight | None = None
    rated_breaking_strength: RatedBreakingStrength | None = None
    total_material_area: MaterialArea | None = None


class BundleSpec(LineDataModel):
    """Describe the number and separation of installed subconductors."""

    subconductor_count: int
    subconductor_spacing: BundleSpacing | None = None

    @model_validator(mode="after")
    def validate_spacing(self) -> "BundleSpec":
        if self.subconductor_count < 1:
            raise ValueError("subconductor_count must be positive")
        if self.subconductor_count > 1 and (
            self.subconductor_spacing is None or self.subconductor_spacing.magnitude <= 0
        ):
            raise ValueError("subconductor_spacing is required and positive for bundles")
        if self.subconductor_count == 1 and self.subconductor_spacing is not None:
            raise ValueError("single conductors cannot specify subconductor_spacing")
        return self


class InsulatorStringSpec(LineDataModel):
    """Specify one circuit's insulator string."""

    insulator_type: Literal["glass", "porcelain", "polymeric"]
    number_of_insulators: int
    insulator_code: str
    insulator_coupling: Literal["ball_and_socket", "y_clevis"]

    @model_validator(mode="after")
    def validate_count(self) -> "InsulatorStringSpec":
        if self.number_of_insulators < 1:
            raise ValueError("number_of_insulators must be positive")
        return self


class Cable(Component, ABC):
    """Hold a reusable manufacturer's selected static cable measurements."""

    catalog_reference: CatalogReference | None = None
    equipment: BareConductorEquipment

    @abstractmethod
    def _cable_kind(self) -> str:
        """Identify the concrete cable role."""


class ConductorSpec(Cable):
    """Select a reusable phase conductor independently of installation."""

    def _cable_kind(self) -> str:
        return "phase"


class GroundWireSpec(Cable):
    """Select a reusable unbundled ground wire."""

    def _cable_kind(self) -> str:
        return "ground"


__all__ = [
    "BareConductorEquipment",
    "BundleSpec",
    "Cable",
    "ConductorSpec",
    "GroundWireSpec",
    "InsulatorStringSpec",
]
