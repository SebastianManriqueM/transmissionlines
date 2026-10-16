import pytest

from transmissionlines.bundle import derived_bundle_values
from transmissionlines.models.cables import BareConductorEquipment, BundleSpec, ConductorSpec
from transmissionlines.units import Quantity


def conductor() -> BareConductorEquipment:
    return BareConductorEquipment(
        diameter_in=1,
        gmr_ft=0.04,
        capacitance_radius_ft=0.02,
        ac_resistance_ohm_kft=0.1,
    )


def test_phase_specs_are_independent_per_circuit() -> None:
    selected = ConductorSpec(name="shared", equipment=conductor())
    first = BundleSpec(subconductor_count=1)
    second = BundleSpec(
        subconductor_count=2,
        subconductor_spacing_in=18,
    )
    first_gmr, first_radius = derived_bundle_values(selected.equipment, first.subconductor_count, first.subconductor_spacing_in)
    second_gmr, second_radius = derived_bundle_values(selected.equipment, second.subconductor_count, second.subconductor_spacing_in)
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
            gmr_ft=0.04,
            capacitance_radius_ft=0.02,
            ac_resistance_ohm_kft=0.1,
        ),
    )
    assert spec.equipment.diameter_in is None
    _, radius = derived_bundle_values(spec.equipment, 1, None)
    assert radius is not None
    assert radius == pytest.approx(0.02)


def test_mechanical_quantities_round_trip_and_reject_wrong_dimensions() -> None:
    equipment = BareConductorEquipment(
        weight_lb_kft=Quantity(0.5, "pound_force / foot"),
        rated_strength_lb=2000,
        total_area_in2=0.75,
    )
    restored = BareConductorEquipment.model_validate_json(equipment.model_dump_json())

    assert restored.weight_lb_kft is not None
    assert restored.weight_lb_kft == pytest.approx(500)
    assert restored.rated_strength_lb is not None
    assert restored.rated_strength_lb == pytest.approx(2000)
    assert restored.total_area_in2 is not None
    assert restored.total_area_in2 == pytest.approx(0.75)
    with pytest.raises(ValueError):
        BareConductorEquipment(weight_lb_kft=Quantity(1, "inch"))
