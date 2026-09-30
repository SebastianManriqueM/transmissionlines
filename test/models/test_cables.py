import pytest

from transmissionlines.bundle import derived_bundle_values
from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec
from transmissionlines.units import BundleSpacing, CableDiameter, CableGMR, ConductorWeight, MaterialArea, RatedBreakingStrength, ResistancePerKft


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


def test_mechanical_quantities_round_trip_and_reject_wrong_dimensions() -> None:
    equipment = BareConductorEquipment(
        weight=ConductorWeight(0.5, "pound_force / foot"),
        rated_breaking_strength=RatedBreakingStrength(2000, "pound_force"),
        total_material_area=MaterialArea(0.75, "inch ** 2"),
    )
    restored = BareConductorEquipment.model_validate_json(equipment.model_dump_json())

    assert restored.weight is not None
    assert restored.weight.to("pound_force / kilofoot").magnitude == pytest.approx(500)
    assert restored.rated_breaking_strength is not None
    assert restored.rated_breaking_strength.magnitude == pytest.approx(2000)
    assert restored.total_material_area is not None
    assert restored.total_material_area.magnitude == pytest.approx(0.75)
    with pytest.raises(ValueError):
        BareConductorEquipment(weight=ConductorWeight(1, "inch"))
