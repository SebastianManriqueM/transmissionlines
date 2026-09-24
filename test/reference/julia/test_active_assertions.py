import numpy as np
import pytest

from transmissionlines.builders.line import geometry_from_records, phase_spec_from_record
from transmissionlines.calculations.cable import ground_wire_gmr
from transmissionlines.calculations.geometry import pairwise_distances
from transmissionlines.catalog.repository import CatalogRepository
from transmissionlines.catalog.schemas import ConductorRecord, GroundWirePositionRecord, PhasePositionRecord
from transmissionlines.units import BundleSpacing


CATALOG = CatalogRepository("data/catalog/v1")


def _geometry(code: str):
    row = CATALOG.select_exact("tower_geometries", structure_code=code)
    phases = CATALOG.table("phase_positions")
    grounds = CATALOG.table("ground_wire_positions")
    phase_records = [PhasePositionRecord.model_validate(r) for r in phases[phases.geometry_id == code].to_dict("records")]
    ground_records = [GroundWirePositionRecord.model_validate(r) for r in grounds[grounds.geometry_id == code].to_dict("records")]
    return row, geometry_from_records(phase_records, ground_records)


def test_original_geometry_examples_are_reproduced() -> None:
    expected = {
        "EX_K4_1": [2.5, 7.0, 5.65685, 4.5, 4.272, 5.0],
        "EX_ST4_14": [26.2467, 52.4934, 1000.34, 26.2467, 1000.0, 1000.34],
        "3L4": [22.6667, 45.3333, 29.1283, 50.3323, 22.6667, 34.3092, 34.3092, 50.3323, 29.1283, 37.1667],
        "5Y2": [37.3162, 37.3162, 23.8537, 23.8537, 43.0, 43.5259, 60.1207, 60.1207, 43.5259, 40.0],
        "3H10": [34.548, 26.0, 20.0, 32.8024, 50.0356, 22.8596, 40.1567, 22.75, 50.0356, 42.75, 65.5, 41.3673, 72.6705, 32.8024, 20.0, 42.75, 44.481, 55.3946, 26.0, 34.548, 40.1567, 22.8596, 22.75, 55.3946, 44.481, 72.6705, 41.3673, 54.5],
    }
    for code, values in expected.items():
        _, geometry = _geometry(code)
        distances = pairwise_distances(geometry.phase_positions + geometry.ground_wire_positions)
        actual = distances[np.triu_indices(len(distances), 1)]
        assert actual[: len(values)] == pytest.approx(values, rel=0.0025)


def test_original_conductor_and_ground_wire_records_are_reproduced() -> None:
    conductor = CATALOG.table("conductors")
    linnet = conductor[conductor.codeword == "Linnet_EX_K4_1"].iloc[0]
    assert linnet.stranding == "26/7"
    assert linnet.internal_reactance_ohm_kft == pytest.approx(0.0854)
    assert linnet.ac_resistance_75_ohm_kft == pytest.approx(0.057955, rel=1e-5)
    pheasant = conductor[(conductor.family == "ACSR") & (conductor.codeword == "Pheasant")].iloc[0]
    assert pheasant.size_kcmil == pytest.approx(1272.0)
    assert pheasant.stranding == "54/19"
    ground = CATALOG.table("ground_wires")
    alumoweld = ground[ground.awg_or_stranding == "19/7"].iloc[0]
    assert alumoweld.size_kcmil == pytest.approx(395.5)
    assert alumoweld.diameter_inch == pytest.approx(0.721)
    assert alumoweld.dc_resistance_ohm_kft == pytest.approx(0.1308)
    linnet_spec = phase_spec_from_record(ConductorRecord.model_validate(linnet.to_dict()), circuit_id="circuit-1", catalog_version="v1")
    assert linnet_spec.bundle_gmr.magnitude == pytest.approx(0.0244, rel=0.005)
    assert linnet.ac_resistance_75_ohm_kft * 5.28 == pytest.approx(0.306, rel=0.005)
    assert float(linnet.internal_reactance_ohm_kft) == pytest.approx(0.0854, rel=0.005)
    pheasant_spec = phase_spec_from_record(ConductorRecord.model_validate(pheasant.to_dict()), circuit_id="circuit-1", subconductor_count=2, subconductor_spacing=BundleSpacing(18, "inch"), catalog_version="v1")
    assert pheasant_spec.bundle_gmr.magnitude == pytest.approx(0.08 * 3.28084, rel=0.008)
    assert pheasant.ac_resistance_75_ohm_kft == pytest.approx(0.017, rel=0.008)
    assert pheasant.internal_reactance_ohm_kft == pytest.approx(0.0704, rel=0.008)
    assert ground_wire_gmr(float(alumoweld.diameter_inch)) == pytest.approx(0.023396, rel=0.002)
    assert ground_wire_gmr(0.251) == pytest.approx(0.00814, rel=0.005)
    assert float(ground_wire_gmr(float(alumoweld.diameter_inch))) == pytest.approx(0.023396, rel=0.002)
