"""Check selected equipment and reusable cross-section construction."""

import pytest

from transmissionlines.catalog.repository import NoCatalogMatch
from transmissionlines.user_api import build


def test_bundle_requires_adjacent_spacing_only_for_multiple_subconductors() -> None:
    assert build.bundle(subconductor_count=1).subconductor_spacing is None
    assert build.bundle(subconductor_count=2, subconductor_spacing_in=18).subconductor_spacing.to("inch").magnitude == 18
    with pytest.raises(ValueError, match="spacing"):
        build.bundle(subconductor_count=2)
    with pytest.raises(ValueError, match="spacing"):
        build.bundle(subconductor_count=1, subconductor_spacing_in=18)


def test_selected_conductor_and_ground_wire_assemble_registered_cross_section() -> None:
    catalog = build.open_catalog()
    geometry_id = catalog.towers(structure_code="3L11")[0]["record_id"]
    circuit_ids = catalog.tower_circuits(geometry_id)
    assert len(circuit_ids) == 2
    conductor_id = catalog.conductors(family="ACSR")[0]["record_id"]
    wire_id = catalog.ground_wires(family="ACSR")[0]["record_id"]
    conductor = build.conductor(catalog, record_id=conductor_id, gmr_ft=0.03)
    wire = build.ground_wire(catalog, record_id=wire_id)
    insulator = dict(insulator_type="glass", number_of_insulators=12,
                     insulator_code="U120B", insulator_coupling="ball_and_socket")
    tower = build.tower(
        catalog, geometry_id=geometry_id, name="tower", ground_wire=wire,
        circuits=[dict(circuit_id=circuit_id, conductor=conductor, bundle=build.bundle(
            subconductor_count=index + 1, subconductor_spacing_in=18 if index else None,
        ), insulator=insulator) for index, circuit_id in enumerate(circuit_ids)],
    )
    line = build.cross_section_line(
        tower, name="study-line", voltage_kv=230, frequency_hz=60,
        earth_resistivity_ohm_m=100, everyday_tension_fraction=0.2,
    )
    system = build.system(name="study")
    registered = build.add_line(system, line)

    assert tower.identification_info.geometry_id == geometry_id
    assert tower.circuits[0].conductor_spec is tower.circuits[1].conductor_spec
    assert registered.configuration.ground_wire_spec.catalog_reference.record_id == wire_id
    assert registered.nominal_voltage.to("kilovolt").magnitude == 230
    assert system.get_component(type(registered), "study-line") is registered
    with pytest.raises(ValueError, match="already registered"):
        build.add_line(system, line)
    with pytest.raises(NoCatalogMatch):
        build.ground_wire(catalog, record_id="absent-wire")


def test_published_gmr_takes_precedence_and_external_completions_have_distinct_names() -> None:
    catalog = build.open_catalog()
    published_id = "ACSS/HS285/TW:area-equal:1033.5:curlew:type-13:standard"
    selected = build.conductor(catalog, record_id=published_id)
    assert selected.equipment.conductor_gmr.to("foot").magnitude == pytest.approx(0.0377)
    with pytest.raises(ValueError, match="already available"):
        build.conductor(catalog, record_id=published_id, gmr_ft=0.04)
    acsr_id = catalog.conductors(family="ACSR")[0]["record_id"]
    with pytest.warns(UserWarning, match="estimated GMR"):
        estimated = build.conductor(catalog, record_id=acsr_id)
    assert estimated.equipment.conductor_gmr is not None
    first = build.conductor(catalog, record_id=acsr_id, gmr_ft=0.03)
    second = build.conductor(catalog, record_id=acsr_id, gmr_ft=0.04)
    assert first.name != second.name
    assert first.catalog_reference == second.catalog_reference
    with pytest.raises(ValueError, match="positive"):
        build.conductor(catalog, record_id=acsr_id, gmr_ft=-0.03)