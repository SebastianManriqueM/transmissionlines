import pytest

from transmissionlines.models.cables import BareConductorEquipment, PhaseConductorSpec
from transmissionlines.units import BundleSpacing, CableDiameter, CableGMR, ResistancePerKft


def conductor() -> BareConductorEquipment:
    return BareConductorEquipment(
        conductor_diameter=CableDiameter(1, "inch"),
        conductor_gmr=CableGMR(0.04, "foot"),
        capacitance_radius=CableGMR(0.02, "foot"),
        ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot"),
    )


def test_phase_specs_are_independent_per_circuit() -> None:
    first = PhaseConductorSpec(conductor=conductor(), circuit_id="c1")
    second = PhaseConductorSpec(
        conductor=conductor(),
        circuit_id="c2",
        subconductor_count=2,
        subconductor_spacing=BundleSpacing(18, "inch"),
    )
    assert first.bundle_gmr != second.bundle_gmr
    assert first.equivalent_radius != second.equivalent_radius


def test_derived_bundle_fields_are_read_only() -> None:
    spec = PhaseConductorSpec(conductor=conductor(), circuit_id="c1")
    with pytest.raises(ValueError, match="frozen"):
        spec.bundle_gmr = CableGMR(1, "foot")
    with pytest.raises(ValueError, match="frozen"):
        spec.equivalent_radius = CableGMR(1, "foot")


def test_capacitance_radius_is_optional_parity_extension() -> None:
    spec = PhaseConductorSpec(
        conductor=BareConductorEquipment(
            conductor_gmr=CableGMR(0.04, "foot"),
            capacitance_radius=CableGMR(0.02, "foot"),
            ac_resistance=ResistancePerKft(0.1, "ohm / kilofoot"),
        ),
        circuit_id="c1",
    )
    assert spec.conductor.conductor_diameter is None
    assert spec.equivalent_radius is not None
    assert spec.equivalent_radius.magnitude == pytest.approx(0.02)
