import pytest

from transmissionlines.bundle import derived_bundle_values
from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec
from transmissionlines.units import BundleSpacing, CableDiameter, CableGMR, ResistancePerKft


def conductor() -> BareConductorEquipment:
    return BareConductorEquipment(
        conductor_diameter=CableDiameter(1, "inch"),
        conductor_gmr=CableGMR(0.04, "foot"),
        capacitance_radius=CableGMR(0.02, "foot"),
        ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot"),
    )


def test_phase_specs_are_independent_per_circuit() -> None:
    selected = ConductorSpec(name="shared", equipment=conductor())
    first = BundleSpec(subconductor_count=1)
    second = BundleSpec(
        subconductor_count=2,
        subconductor_spacing=BundleSpacing(18, "inch"),
    )
    first_gmr, first_radius = derived_bundle_values(selected.equipment, first.subconductor_count, first.subconductor_spacing)
    second_gmr, second_radius = derived_bundle_values(selected.equipment, second.subconductor_count, second.subconductor_spacing)
    assert first_gmr != second_gmr
    assert first_radius != second_radius


def test_derived_bundle_fields_are_read_only() -> None:
    spec = BundleSpec(subconductor_count=1)
    assert not hasattr(spec, "bundle_gmr")
    assert not hasattr(spec, "equivalent_radius")
    with pytest.raises(ValueError, match="frozen"):
        spec.subconductor_count = 2


def test_capacitance_radius_is_optional_parity_extension() -> None:
    spec = ConductorSpec(
        name="source",
        equipment=BareConductorEquipment(
            conductor_gmr=CableGMR(0.04, "foot"),
            capacitance_radius=CableGMR(0.02, "foot"),
            ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot"),
        ),
    )
    assert spec.equipment.conductor_diameter is None
    _, radius = derived_bundle_values(spec.equipment, 1, None)
    assert radius is not None
    assert radius.magnitude == pytest.approx(0.02)
